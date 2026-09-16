"""Phase 46 — project analytics read-model (real PG)."""

import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.analytics_service import project_analytics, study_streak_days
from app.services.growth_service import project_growth

T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _seed(db, suffix: str):
    user = User(email=f"an-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    for status in ("ready", "ready", "processing"):
        db.add(Material(project_id=project.id, filename="d.pdf",
                        storage_path=f"/tmp/{uuid.uuid4().hex}.pdf", status=status))
    topic = Topic(project_id=project.id, title="T")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
    db.add(sub)
    db.flush()
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C", summary="S.")
    db.add(concept)
    db.flush()
    db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                           evidence_type="mcq", raw_score=80, created_at=T0))
    quiz = Quiz(project_id=project.id, mode="practice", question_count=1)
    db.add(quiz)
    db.flush()
    db.add(QuizAttempt(quiz_id=quiz.id, user_id=user.id,
                       completed_at=datetime(2026, 9, 2, tzinfo=timezone.utc)))
    db.add(QuizAttempt(quiz_id=quiz.id, user_id=user.id))
    db.commit()
    return user, project


def test_aggregates_match_domain_and_growth():
    db = _session()
    try:
        user, project = _seed(db, uuid.uuid4().hex[:8])
        stats = project_analytics(db, user_id=user.id, project_id=project.id)
        assert stats.materials_total == 3
        assert stats.materials_by_status == {"ready": 2, "processing": 1}
        assert stats.topics_count == 1 and stats.concepts_count == 1
        assert stats.quiz_attempts == 2 and stats.quiz_attempts_completed == 1
        growth = project_growth(db, user_id=user.id, project_id=project.id)
        assert (stats.avg_mcq, stats.avg_applied) == (growth.avg_mcq, growth.avg_applied) == (80.0, None)
        assert stats.evidenced_concepts == 1
        assert stats.tutor_interactions is None  # untracked — no invented counter
        with pytest.raises(LookupError):
            project_analytics(db, user_id=user.id, project_id=uuid.uuid4())
    finally:
        db.close()


def test_study_streak_counts_consecutive_days():
    from datetime import timedelta

    db = _session()
    try:
        user, project = _seed(db, uuid.uuid4().hex[:8])
        concept = db.query(Concept).filter(Concept.project_id == project.id).one()
        today = datetime.now(timezone.utc).date()

        def _evidence(days_ago: int):
            at = datetime.combine(today - timedelta(days=days_ago), datetime.min.time(),
                                  tzinfo=timezone.utc)
            db.add(MasteryEvidence(user_id=user.id, project_id=project.id,
                                   concept_id=concept.id, evidence_type="mcq",
                                   raw_score=70, created_at=at))

        # today + yesterday + (gap) + 3 days ago -> streak of 2
        _evidence(0)
        _evidence(1)
        _evidence(3)
        db.commit()
        assert study_streak_days(db, user_id=user.id, project_id=project.id) == 2
        stats = project_analytics(db, user_id=user.id, project_id=project.id)
        assert stats.streak_days == 2
    finally:
        db.close()


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


def test_api_empty_isolation_and_auth():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        headers = {}
        for who in ("a", "b"):
            email = f"anapi-{who}-{suffix}@example.com"
            client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
            resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
            headers[who] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers["a"])
        resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=headers["a"])
        pid = resp.json()["id"]
        body = client.get(f"/api/v1/projects/{pid}/analytics", headers=headers["a"]).json()
        assert body == {"materials_total": 0, "materials_by_status": {}, "topics_count": 0,
                        "concepts_count": 0, "quiz_attempts": 0, "quiz_attempts_completed": 0,
                        "avg_mcq": None, "avg_applied": None, "evidenced_concepts": 0,
                        "streak_days": 0, "tutor_interactions": None}
        assert client.get(f"/api/v1/projects/{pid}/analytics", headers=headers["b"]).status_code == 404
        assert client.get(f"/api/v1/projects/{pid}/analytics").status_code in (401, 403)
        assert client.get(f"/api/v1/projects/{uuid.uuid4()}/analytics", headers=headers["a"]).status_code == 404
    finally:
        _teardown(engine)
