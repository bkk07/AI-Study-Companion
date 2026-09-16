"""Phase 48 — every failure path emits one JSON envelope (real PG).

Envelope: {"error": {"code": "<stable>", "message": "<safe>", "details?": ...}}.
Status codes are unchanged; only the body shape is unified. Secrets and
tracebacks must never appear in 5xx bodies.
"""

import os
import uuid
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.exceptions import INTERNAL_ERROR_MESSAGE, error_code_for_status
from app.core.jwt import create_access_token
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.rag import RagChunk, RagContext


def _setup():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def _teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def _login(client: TestClient, email: str) -> dict:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_validation_error_envelope():
    client, engine = _setup()
    try:
        resp = client.post(
            "/api/v1/auth/register", json={"email": "not-an-email", "password": "supersecret123"}
        )
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert set(body) == {"error"}
        err = body["error"]
        assert err["code"] == "validation_error"
        assert isinstance(err["message"], str) and err["message"]
        assert isinstance(err.get("details"), list) and err["details"]
        assert {"loc", "msg", "type"} <= set(err["details"][0])
    finally:
        _teardown(engine)


def test_unauthenticated_envelope_keeps_challenge_header():
    client, engine = _setup()
    try:
        resp = client.get("/api/v1/spaces")
        assert resp.status_code == 401, resp.text
        assert resp.json()["error"]["code"] == "authentication_required"
        assert "bearer" in resp.headers.get("www-authenticate", "").lower()
    finally:
        _teardown(engine)


def test_expired_token_envelope():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        email = f"err-exp-{suffix}@example.com"
        resp = client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        expired = create_access_token(subject=resp.json()["id"], expires_delta=timedelta(seconds=-1))
        resp = client.get("/api/v1/spaces", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401, resp.text
        err = resp.json()["error"]
        assert err["code"] == "authentication_required"
        assert "expired" in err["message"].lower()
    finally:
        _teardown(engine)


def test_forbidden_envelope():
    client, engine = _setup()
    try:
        h = _login(client, f"err-403-{uuid.uuid4().hex[:8]}@example.com")
        resp = client.get("/api/v1/admin/users", headers=h)
        assert resp.status_code == 403, resp.text
        err = resp.json()["error"]
        assert err == {"code": "forbidden", "message": "Admin access required"}
    finally:
        _teardown(engine)


def test_not_found_envelope_has_no_legacy_shape():
    client, engine = _setup()
    try:
        h = _login(client, f"err-404-{uuid.uuid4().hex[:8]}@example.com")
        resp = client.get(f"/api/v1/spaces/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404, resp.text
        body = resp.json()
        assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
        assert body["error"] == {"code": "not_found", "message": "Space not found"}
    finally:
        _teardown(engine)


def test_bad_request_envelope():
    client, engine = _setup()
    try:
        email = f"err-400-{uuid.uuid4().hex[:8]}@example.com"
        assert client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"}).status_code == 201
        resp = client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        assert resp.status_code == 400, resp.text
        assert resp.json()["error"] == {"code": "bad_request", "message": "Email already registered"}
    finally:
        _teardown(engine)


def test_unhandled_exception_never_leaks_internals():
    client, engine = _setup()
    try:
        secret = "traceback SELECT hashed_password FROM users"

        def boom():
            raise RuntimeError(secret)

        app.dependency_overrides[get_current_user] = boom
        quiet = TestClient(app, raise_server_exceptions=False)
        resp = quiet.get("/api/v1/spaces")
        assert resp.status_code == 500, resp.text
        assert resp.json()["error"] == {"code": "internal_error", "message": INTERNAL_ERROR_MESSAGE}
        assert secret not in resp.text and "hashed_password" not in resp.text
    finally:
        _teardown(engine)


def test_upstream_502_envelope():
    client, engine = _setup()
    try:
        h = _login(client, f"err-502-{uuid.uuid4().hex[:8]}@example.com")
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=h)
        assert resp.status_code == 201, resp.text
        resp = client.post(
            f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=h
        )
        assert resp.status_code == 201, resp.text
        pid = resp.json()["id"]
        chunk = RagChunk(
            chunk_id=uuid.uuid4(), material_id=uuid.uuid4(), content="Slope content.",
            page_number=1, source_name="doc.pdf", chunk_index=0, score=0.05,
        )
        with (
            patch("app.services.tutor_service.rag_service") as rag,
            patch("app.services.tutor_service.groq_client") as groq,
        ):
            rag.assemble_context.return_value = RagContext(
                query="Q?", scope_project_id=uuid.UUID(pid),
                chunks=[chunk], total_chars=14, truncated=False,
            )
            groq.chat_json.return_value = {"unexpected": "shape"}  # malformed provider payload
            resp = client.post(f"/api/v1/projects/{pid}/tutor/ask", json={"question": "Q?"}, headers=h)
        assert resp.status_code == 502, resp.text
        assert resp.json()["error"] == {
            "code": "upstream_unavailable",
            "message": "Tutor AI provider returned an unusable response",
        }
    finally:
        _teardown(engine)


def test_status_code_table_covers_all_contract_categories():
    assert error_code_for_status(400) == "bad_request"
    assert error_code_for_status(401) == "authentication_required"
    assert error_code_for_status(403) == "forbidden"
    assert error_code_for_status(404) == "not_found"
    assert error_code_for_status(413) == "payload_too_large"
    assert error_code_for_status(422) == "validation_error"
    assert error_code_for_status(429) == "rate_limited"  # no producer yet (Phase 49); mapping ready
    assert error_code_for_status(500) == "internal_error"
    assert error_code_for_status(502) == "upstream_unavailable"
    assert error_code_for_status(418) == "bad_request"  # unknown 4xx falls back sanely
    assert error_code_for_status(599) == "internal_error"  # unknown 5xx never leaks by default
