"""Phase 44 — dashboard bridge: composition over existing engines (real PG)."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic

T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


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


def _users(client: TestClient, engine):
    suffix = uuid.uuid4().hex[:8]
    ids, headers = {}, {}
    for who in ("a", "b"):
        email = f"dash-{who}-{suffix}@example.com"
        client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
        assert resp.status_code == 200, resp.text
        headers[who] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers["a"])
    assert resp.status_code == 201, resp.text
    resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=headers["a"])
    assert resp.status_code == 201, resp.text
    ids["pid"] = resp.json()["id"]
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        me = None
        from app.models.user import User

        me = db.query(User).filter(User.email == f"dash-a-{suffix}@example.com").one()
        ids["uid"] = str(me.id)
        project = db.get(Project, uuid.UUID(ids["pid"]))
        topic = Topic(project_id=project.id, title="Algebra", created_at=T0)
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="Linear", created_at=T0)
        db.add(sub)
        db.flush()
        gap = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope",
                      summary="Rise.", created_at=T0)
        calm = Concept(project_id=project.id, subtopic_id=sub.id, title="Intercept",
                       summary="Cross.", created_at=T0)
        db.add_all([gap, calm])
        db.flush()
        ids["gap"], ids["calm"] = str(gap.id), str(calm.id)
        # gap concept: 3x mcq @90 + 1x explain_back @40 -> mcq~90, applied 40, gap 50 flags:
        for i, score in enumerate((90, 90, 90)):
            db.add(MasteryEvidence(user_id=me.id, project_id=project.id, concept_id=gap.id,
                                   evidence_type="mcq", raw_score=score, created_at=T0 + timedelta(days=i)))
        db.add(MasteryEvidence(user_id=me.id, project_id=project.id, concept_id=gap.id,
                               evidence_type="explain_back", raw_score=40, feedback="Vague.",
                               created_at=T0 + timedelta(days=3)))
        # calm concept: mcq ~70 + applied 73 (no primary gap) + underconfident quiz answers:
        for i, score in enumerate((70, 70, 70)):
            db.add(MasteryEvidence(user_id=me.id, project_id=project.id, concept_id=calm.id,
                                   evidence_type="mcq", raw_score=score,
                                   created_at=T0 + timedelta(days=i)))
        for i, score in enumerate((70, 80)):
            db.add(MasteryEvidence(user_id=me.id, project_id=project.id, concept_id=calm.id,
                                   evidence_type="explain_back", raw_score=score, feedback="OK.",
                                   created_at=T0 + timedelta(days=i)))
        quiz = Quiz(project_id=project.id, mode="practice", question_count=2)
        db.add(quiz)
        db.flush()
        q1 = QuizQuestion(quiz_id=quiz.id, concept_id=calm.id, question_text="Q1?",
                          options=["a", "b"], correct_index=0, difficulty="easy")
        q2 = QuizQuestion(quiz_id=quiz.id, concept_id=calm.id, question_text="Q2?",
                          options=["a", "b"], correct_index=1, difficulty="easy")
        db.add_all([q1, q2])
        db.flush()
        attempt = QuizAttempt(quiz_id=quiz.id, user_id=me.id)
        db.add(attempt)
        db.flush()
        db.add_all([
            QuizAnswer(attempt_id=attempt.id, question_id=q1.id, selected_index=0,
                       is_correct=True, confidence=1),
            QuizAnswer(attempt_id=attempt.id, question_id=q2.id, selected_index=1,
                       is_correct=True, confidence=2),
        ])
        db.commit()
    finally:
        db.close()
    return ids, headers


def test_dashboard_composes_mastery_mismatch_and_paths():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        with patch("app.services.dashboard_service.datetime") as _dt:
            _dt.now.return_value = datetime(2026, 9, 16, tzinfo=timezone.utc)
            resp = client.get(f"/api/v1/projects/{ids['pid']}/dashboard", headers=headers["a"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["recommendation"] is None  # nothing issued yet
        by_title = {c["title"]: c for c in body["concepts"]}
        assert set(by_title) == {"Slope", "Intercept"}
        slope = by_title["Slope"]
        assert slope["topic"] == "Algebra" and slope["subtopic"] == "Linear"
        assert slope["mcq"] == pytest.approx(90.0) and slope["mcq_count"] == 3
        assert slope["applied"] == pytest.approx(40.0) and slope["applied_count"] == 1
        assert slope["mismatch"]["mismatch_type"] == "mcq_high_applied_low"
        assert "50.0" in slope["mismatch"]["reason"]
        calm = by_title["Intercept"]
        assert calm["mcq"] == pytest.approx(70.0) and calm["mcq_count"] == 3
        assert calm["applied"] == pytest.approx(70 + 0.3 * 10)
        assert calm["mismatch"]["mismatch_type"] == "underconfident"  # 100% acc, conf 1.5
        # calibration exposure for the attention cards (rated answers only)
        assert calm["avg_confidence"] == pytest.approx(1.5)
        assert calm["accuracy"] == pytest.approx(1.0)
        assert calm["evaluated_count"] == 2
        assert slope["avg_confidence"] is None
        assert slope["accuracy"] is None
        assert slope["evaluated_count"] == 0
    finally:
        _teardown(engine)


def test_refresh_accept_dismiss_lifecycle():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        base = f"/api/v1/projects/{ids['pid']}/dashboard"
        assert client.post(f"{base}/accept", headers=headers["a"]).status_code == 404  # none active
        with patch("app.services.dashboard_service.datetime") as _dt:
            _dt.now.return_value = datetime(2026, 9, 16, tzinfo=timezone.utc)
            first = client.post(f"{base}/refresh", headers=headers["a"])
        assert first.status_code == 201, first.text
        assert first.json()["status"] == "active" and "reasoning" in first.json()
        got = client.get(base, headers=headers["a"])
        assert got.json()["recommendation"]["id"] == first.json()["id"]
        assert client.post(f"{base}/dismiss", headers=headers["a"]).json()["status"] == "dismissed"
        assert client.get(base, headers=headers["a"]).json()["recommendation"]["status"] == "dismissed"
        with patch("app.services.dashboard_service.datetime") as _dt:
            _dt.now.return_value = datetime(2026, 9, 16, tzinfo=timezone.utc)
            second = client.post(f"{base}/refresh", headers=headers["a"])
        assert second.json()["id"] != first.json()["id"]
        assert client.get(base, headers=headers["a"]).json()["recommendation"]["id"] == second.json()["id"]
    finally:
        _teardown(engine)


def test_dashboard_isolation_and_auth():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        base = f"/api/v1/projects/{ids['pid']}/dashboard"
        assert client.get(base, headers=headers["b"]).status_code == 404
        assert client.get(base).status_code in (401, 403)
        assert client.post(f"{base}/refresh", headers=headers["b"]).status_code == 404
        assert client.get(f"/api/v1/projects/{uuid.uuid4()}/dashboard", headers=headers["a"]).status_code == 404
    finally:
        _teardown(engine)
