"""Phase 37 bridge — quiz/attempt endpoints (real auth/DB, stubbed generation)."""

import os
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.quiz_generation_service import QuizGenerationError


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
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="Rise.")
        db.add(concept)
        db.flush()
        quiz = Quiz(project_id=project.id, mode="practice", question_count=2)
        db.add(quiz)
        db.flush()
        q1 = QuizQuestion(quiz_id=quiz.id, concept_id=concept.id, question_text="Slope of y=2x?",
                          options=["1", "2", "3"], correct_index=1, difficulty="easy")
        q2 = QuizQuestion(quiz_id=quiz.id, concept_id=concept.id, question_text="Intercept of y=x+5?",
                          options=["0", "5"], correct_index=1, difficulty="easy")
        db.add_all([q1, q2])
        db.commit()
        return {"pid": str(project.id), "qid": str(quiz.id), "cid": str(concept.id),
                "q1": str(q1.id), "q2": str(q2.id)}
    finally:
        db.close()


def _users():
    client, engine = _setup()
    suffix = uuid.uuid4().hex[:8]
    ha = _register_login(client, f"qapi-a-{suffix}@example.com")
    hb = _register_login(client, f"qapi-b-{suffix}@example.com")
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=ha)
    assert resp.status_code == 201, resp.text
    resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=ha)
    assert resp.status_code == 201, resp.text
    ids = _seed_quiz(engine, uuid.UUID(resp.json()["id"]))
    return client, engine, ids, ha, hb


def test_generate_wires_service_and_maps_errors():
    client, engine, ids, ha, _ = _users()
    try:
        fake = SimpleNamespace(id=uuid.uuid4(), question_count=2)
        with patch("app.api.v1.quizzes.quiz_generation_service") as svc:
            svc.generate_quiz.return_value = fake
            resp = client.post(f"/api/v1/projects/{ids['pid']}/quizzes/generate",
                               json={"concept_id": ids["cid"], "num_questions": 2}, headers=ha)
            assert resp.status_code == 201, resp.text
            assert resp.json() == {"quiz_id": str(fake.id), "question_count": 2}
            svc.QuizGenerationError = QuizGenerationError
            svc.generate_quiz.side_effect = QuizGenerationError("bad output")
            assert client.post(f"/api/v1/projects/{ids['pid']}/quizzes/generate",
                               json={"concept_id": ids["cid"]}, headers=ha).status_code == 422
            svc.generate_quiz.side_effect = LookupError("nope")
            assert client.post(f"/api/v1/projects/{ids['pid']}/quizzes/generate",
                               json={"concept_id": ids["cid"]}, headers=ha).status_code == 404
    finally:
        _teardown(engine)


def test_attempt_flow_scores_and_locks():
    client, engine, ids, ha, _ = _users()
    try:
        resp = client.post(f"/api/v1/projects/{ids['pid']}/quizzes/{ids['qid']}/attempts", headers=ha)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "correct_index" not in resp.text  # answers hidden before answering
        assert len(body["questions"]) == 2
        aid = body["attempt_id"]

        base = f"/api/v1/projects/{ids['pid']}/quizzes/attempts/{aid}/answers"
        r1 = client.post(base, json={"question_id": ids["q1"], "selected_index": 1, "confidence": 4}, headers=ha)
        assert r1.status_code == 200, r1.text
        assert r1.json()["is_correct"] is True and r1.json()["correct_index"] == 1
        r2 = client.post(base, json={"question_id": ids["q2"], "selected_index": 0, "confidence": 2}, headers=ha)
        assert r2.json()["is_correct"] is False and r2.json()["correct_index"] == 1
        assert r2.json()["answered_count"] == 2 and r2.json()["correct_count"] == 1
        # duplicate + out-of-range rejected, confidence persisted
        assert client.post(base, json={"question_id": ids["q1"], "selected_index": 1}, headers=ha).status_code == 400
        assert client.post(base, json={"question_id": ids["q2"], "selected_index": 9}, headers=ha).status_code == 400
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            confs = sorted(a.confidence for a in db.query(QuizAnswer).filter(QuizAnswer.attempt_id == uuid.UUID(aid)).all())
            assert confs == [2, 4]
        finally:
            db.close()

        done = client.post(f"/api/v1/projects/{ids['pid']}/quizzes/attempts/{aid}/complete", headers=ha)
        assert done.status_code == 200, done.text
        assert done.json()["score"] == 50.0 and done.json()["correct_count"] == 1
        assert client.post(base, json={"question_id": ids["q1"], "selected_index": 1}, headers=ha).status_code == 400
    finally:
        _teardown(engine)


def test_quiz_isolation_and_auth():
    client, engine, ids, ha, hb = _users()
    try:
        assert client.post(f"/api/v1/projects/{ids['pid']}/quizzes/{ids['qid']}/attempts", headers=hb).status_code == 404
        assert client.post(f"/api/v1/projects/{ids['pid']}/quizzes/{ids['qid']}/attempts").status_code in (401, 403)
        resp = client.post(f"/api/v1/projects/{ids['pid']}/quizzes/{ids['qid']}/attempts", headers=ha)
        aid = resp.json()["attempt_id"]
        base = f"/api/v1/projects/{ids['pid']}/quizzes/attempts/{aid}/answers"
        assert client.post(base, json={"question_id": ids["q1"], "selected_index": 1}, headers=hb).status_code == 404
        assert client.post(f"/api/v1/projects/{uuid.uuid4()}/quizzes/{ids['qid']}/attempts", headers=ha).status_code == 404
    finally:
        _teardown(engine)
