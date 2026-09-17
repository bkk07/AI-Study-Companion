"""Phase 5 — tracking never breaks requests: metering/event failures still HTTP 200 (real PG)."""

import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.subtopic import Subtopic
from app.models.topic import Topic
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


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_tutor_ask_still_200_when_metering_db_down():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        ha = _register_login(client, f"res-t-{suffix}@example.com")
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=ha)
        pid = client.post(
            f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=ha
        ).json()["id"]
        chunk = RagChunk(chunk_id=uuid.uuid4(), material_id=uuid.uuid4(), content="Slope is rise.",
                         page_number=1, source_name="d.pdf", chunk_index=0, score=0.05)
        ctx = RagContext(query="What is slope?", scope_project_id=uuid.UUID(pid),
                         chunks=[chunk], total_chars=14, truncated=False)
        payload = {"choices": [{"message": {"content": '{"answer": "Slope is rise [1]."}'}}],
                   "usage": {"prompt_tokens": 50, "completion_tokens": 10}}
        with (
            patch("app.services.tutor_service.rag_service") as rag,
            patch("app.services.ai.groq_client.httpx.post", return_value=_FakeResp(payload)),
            patch("app.services.ai.groq_client.get_settings") as gs,
            patch("app.services.ai_usage_service.SessionLocal",
                  side_effect=RuntimeError("metering db down")),
        ):
            rag.assemble_context.return_value = ctx
            gs.return_value.llm_provider = "groq"
            gs.return_value.groq_api_key = "test-key"
            gs.return_value.groq_model = "test-model"
            resp = client.post(f"/api/v1/projects/{pid}/tutor/ask",
                               json={"question": "What is slope?"}, headers=ha)
        assert resp.status_code == 200, resp.text
        assert resp.json()["answer"] == "Slope is rise [1]."
    finally:
        _teardown(engine)


def _seed_quiz(engine, project_id: uuid.UUID):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        project = db.get(Project, project_id)
        topic = Topic(project_id=project.id, title="T")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
        db.add(sub)
        db.flush()
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="R.")
        db.add(concept)
        db.flush()
        quiz = Quiz(project_id=project.id, mode="practice", question_count=1)
        db.add(quiz)
        db.flush()
        q = QuizQuestion(quiz_id=quiz.id, concept_id=concept.id, question_text="Slope?",
                         options=["1", "2"], correct_index=1, difficulty="easy")
        db.add(q)
        db.commit()
        return str(quiz.id), str(q.id)
    finally:
        db.close()


def test_quiz_submit_and_complete_still_200_when_event_write_fails():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        ha = _register_login(client, f"res-q-{suffix}@example.com")
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=ha)
        pid = client.post(
            f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=ha
        ).json()["id"]
        qid, question_id = _seed_quiz(engine, uuid.UUID(pid))
        resp = client.post(f"/api/v1/projects/{pid}/quizzes/{qid}/attempts", headers=ha)
        assert resp.status_code == 201, resp.text
        aid = resp.json()["attempt_id"]
        base = f"/api/v1/projects/{pid}/quizzes/attempts/{aid}/answers"
        with patch("app.services.activity_service.pg_insert", side_effect=RuntimeError("events down")):
            r1 = client.post(base, json={"question_id": question_id, "selected_index": 1},
                             headers=ha)
            assert r1.status_code == 200, r1.text
            assert r1.json()["is_correct"] is True
            done = client.post(f"/api/v1/projects/{pid}/quizzes/attempts/{aid}/complete",
                               headers=ha)
            assert done.status_code == 200, done.text
            assert done.json()["score"] == 100.0
    finally:
        _teardown(engine)
