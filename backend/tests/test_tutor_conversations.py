"""Tutor conversation persistence: threads, history, isolation (real PG)."""

import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
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


def _register_login(client: TestClient, email: str) -> dict:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _users():
    client, engine = _setup()
    suffix = uuid.uuid4().hex[:8]
    ha = _register_login(client, f"convo-a-{suffix}@example.com")
    hb = _register_login(client, f"convo-b-{suffix}@example.com")
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=ha)
    assert resp.status_code == 201, resp.text
    resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=ha)
    assert resp.status_code == 201, resp.text
    return client, engine, resp.json()["id"], ha, hb


def _chunk():
    return RagChunk(
        chunk_id=uuid.uuid4(), material_id=uuid.uuid4(), content="Slope is rise over run.",
        page_number=2, source_name="doc.pdf", chunk_index=3, score=0.05,
    )


def _ctx(pid: str, chunks, query: str = "q") -> RagContext:
    return RagContext(
        query=query, scope_project_id=uuid.UUID(pid),
        chunks=chunks, total_chars=sum(len(c.content) for c in chunks), truncated=False,
    )


def test_create_chat_list_and_reload_history():
    client, engine, pid, ha, _ = _users()
    try:
        base = f"/api/v1/projects/{pid}/tutor"
        assert client.get(f"{base}/conversations", headers=ha).json() == []
        resp = client.post(f"{base}/conversations", json={}, headers=ha)
        assert resp.status_code == 201, resp.text
        cid = resp.json()["id"]
        assert resp.json()["title"] == "New chat"

        chunks = [_chunk()]
        with (
            patch("app.services.tutor_service.rag_service") as rag,
            patch("app.services.tutor_service.groq_client") as groq,
        ):
            rag.assemble_context.return_value = _ctx(pid, chunks, "What is slope?")
            groq.chat_json.return_value = {
                "answer": "Slope is rise over run.",
                "follow_ups": ["What is intercept?"],
            }
            resp = client.post(f"{base}/conversations/{cid}/messages",
                               json={"question": "What is slope?"}, headers=ha)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["conversation_id"] == cid
        assert body["supported"] is True
        assert body["follow_ups"] == ["What is intercept?"]
        assert body["citations"][0]["excerpt"] == "Slope is rise over run."
        assert body["citations"][0]["page_number"] == 2

        listing = client.get(f"{base}/conversations", headers=ha).json()
        assert len(listing) == 1
        assert listing[0]["id"] == cid and listing[0]["message_count"] == 2
        assert listing[0]["title"] == "What is slope?"  # auto-titled

        detail = client.get(f"{base}/conversations/{cid}", headers=ha).json()
        assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
        assert detail["messages"][0]["content"] == "What is slope?"
        assert detail["messages"][1]["content"] == "Slope is rise over run."
        assert detail["messages"][1]["follow_ups"] == ["What is intercept?"]
        assert detail["messages"][1]["citations"][0]["source_name"] == "doc.pdf"
    finally:
        _teardown(engine)


def test_greeting_persisted_without_llm():
    client, engine, pid, ha, _ = _users()
    try:
        base = f"/api/v1/projects/{pid}/tutor"
        cid = client.post(f"{base}/conversations", json={}, headers=ha).json()["id"]
        with (
            patch("app.services.tutor_service.rag_service") as rag,
            patch("app.services.tutor_service.groq_client") as groq,
        ):
            resp = client.post(f"{base}/conversations/{cid}/messages",
                               json={"question": "greetings"}, headers=ha)
            assert resp.status_code == 200, resp.text
            assert resp.json()["supported"] is True
            assert resp.json()["citations"] == []
            rag.assemble_context.assert_not_called()
            groq.chat_json.assert_not_called()
        detail = client.get(f"{base}/conversations/{cid}", headers=ha).json()
        assert len(detail["messages"]) == 2
    finally:
        _teardown(engine)


def test_isolation_across_users_and_projects():
    client, engine, pid, ha, hb = _users()
    try:
        base = f"/api/v1/projects/{pid}/tutor"
        cid = client.post(f"{base}/conversations", json={}, headers=ha).json()["id"]
        # other user cannot reach this project at all (ownership gate first)
        assert client.get(f"{base}/conversations", headers=hb).status_code == 404
        assert client.get(f"{base}/conversations/{cid}", headers=hb).status_code == 404
        assert client.post(f"{base}/conversations/{cid}/messages",
                           json={"question": "Hi?"}, headers=hb).status_code == 404
        assert client.delete(f"{base}/conversations/{cid}", headers=hb).status_code == 404
        # same owner, foreign project id: invisible
        assert client.get(f"/api/v1/projects/{uuid.uuid4()}/tutor/conversations/{cid}",
                          headers=ha).status_code == 404
        assert client.post(f"{base}/conversations", json={}).status_code in (401, 403)
        # delete works for owner
        assert client.delete(f"{base}/conversations/{cid}", headers=ha).status_code == 204
        assert client.get(f"{base}/conversations/{cid}", headers=ha).status_code == 404
    finally:
        _teardown(engine)


def test_empty_message_rejected():
    client, engine, pid, ha, _ = _users()
    try:
        base = f"/api/v1/projects/{pid}/tutor"
        cid = client.post(f"{base}/conversations", json={}, headers=ha).json()["id"]
        assert client.post(f"{base}/conversations/{cid}/messages",
                           json={"question": "   "}, headers=ha).status_code == 400
    finally:
        _teardown(engine)
