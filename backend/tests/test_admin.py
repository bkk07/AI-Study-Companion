"""Phase 47 — admin boundary: same JWT identity, separate privilege (real PG)."""

import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.space import Space
from app.models.user import User


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


def _make_admin(engine, email: str) -> None:
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        user = db.query(User).filter(User.email == email).one()
        user.is_admin = True
        db.add(Space(user_id=user.id, name="admin-space"))
        db.commit()
    finally:
        db.close()


def _users(client: TestClient, engine):
    suffix = uuid.uuid4().hex[:8]
    admin_email = f"adm-{suffix}@example.com"
    user_email = f"usr-{suffix}@example.com"
    ha, hu = _login(client, admin_email), _login(client, user_email)
    _make_admin(engine, admin_email)
    return ha, hu, admin_email, user_email


def test_anonymous_and_non_admin_refused():
    client, engine = _setup()
    try:
        ha, hu, _, _ = _users(client, engine)
        assert client.get("/api/v1/admin/users").status_code == 401
        assert client.get("/api/v1/admin/overview").status_code == 401
        assert client.get("/api/v1/admin/users", headers=hu).status_code == 403
        assert client.get("/api/v1/admin/overview", headers=hu).status_code == 403
        assert client.get("/api/v1/admin/users", headers=ha).status_code == 200
    finally:
        _teardown(engine)


def test_admin_sees_users_without_passwords():
    client, engine = _setup()
    try:
        ha, _, admin_email, user_email = _users(client, engine)
        suffix = admin_email.split("-")[1].split("@")[0]
        resp = client.get("/api/v1/admin/users", params={"q": suffix}, headers=ha)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body) == {"items", "total", "limit", "offset"}
        got = {u["email"]: u for u in body["items"]}
        assert {admin_email, user_email} <= set(got)
        assert got[admin_email]["is_admin"] is True and got[user_email]["is_admin"] is False
        assert "hashed_password" not in resp.text
        for u in body["items"]:
            assert set(u) == {"id", "email", "is_admin", "created_at", "project_count", "last_active"}
            assert isinstance(u["project_count"], int) and u["project_count"] >= 0
        assert body["total"] >= 2 and body["limit"] == 25 and body["offset"] == 0
    finally:
        _teardown(engine)


def test_users_pagination_and_search():
    client, engine = _setup()
    try:
        ha, _, admin_email, user_email = _users(client, engine)
        first = client.get("/api/v1/admin/users", params={"limit": 1, "offset": 0}, headers=ha)
        assert first.status_code == 200, first.text
        assert len(first.json()["items"]) == 1
        assert first.json()["total"] >= 2
        second = client.get("/api/v1/admin/users", params={"limit": 1, "offset": 1}, headers=ha)
        assert second.json()["items"][0]["id"] != first.json()["items"][0]["id"]
        found = client.get("/api/v1/admin/users", params={"q": admin_email}, headers=ha)
        assert found.json()["total"] == 1
        assert found.json()["items"][0]["email"] == admin_email
        missing = client.get("/api/v1/admin/users", params={"q": "no-such-user-xyz"}, headers=ha)
        assert missing.json()["total"] == 0 and missing.json()["items"] == []
    finally:
        _teardown(engine)


def test_overview_counts_match_domain():
    client, engine = _setup()
    try:
        ha, _, _, _ = _users(client, engine)
        resp = client.get("/api/v1/admin/overview", headers=ha)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body) == {"users", "spaces", "projects", "materials", "quizzes",
                             "quiz_attempts", "evidence_rows", "recommendations",
                             "quiz_attempts_week", "cost_week_usd"}
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            assert body["users"] == db.query(User).count()
            assert body["spaces"] == db.query(Space).count() >= 1
        finally:
            db.close()
        assert all(isinstance(v, int) and v >= 0 for k, v in body.items() if k != "cost_week_usd")
        assert body["cost_week_usd"] is None or body["cost_week_usd"] >= 0
    finally:
        _teardown(engine)


def test_privilege_cannot_be_self_granted():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        email = f"esc-{suffix}@example.com"
        resp = client.post("/api/v1/auth/register",
                           json={"email": email, "password": "supersecret123", "is_admin": True})
        assert resp.status_code == 201, resp.text
        assert resp.json()["is_admin"] is False  # extra field ignored, never honored
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            assert db.query(User).filter(User.email == email).one().is_admin is False
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()
    finally:
        _teardown(engine)
