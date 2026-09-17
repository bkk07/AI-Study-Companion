"""Global streak: consecutive UTC days with evidence in any project (real PG)."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.analytics_service import study_streak_days_global


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


def _seed_user_project_concept(db, suffix):
    user = User(email=f"stk-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    topic = Topic(project_id=project.id, title="T")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
    db.add(sub)
    db.flush()
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C", summary="S.")
    db.add(concept)
    db.flush()
    db.commit()
    return user, project, concept


def _add_evidence(db, user, project, concept, days_ago: int):
    moment = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                           evidence_type="mcq", source="practice", raw_score=Decimal("80"),
                           created_at=moment))
    db.commit()


def test_global_streak_counts_any_project_and_resets_on_gap():
    client, engine = _setup()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user, project, concept = _seed_user_project_concept(db, suffix)
        uid = user.id
        assert study_streak_days_global(db, user_id=uid) == 0
        _add_evidence(db, user, project, concept, days_ago=2)
        _add_evidence(db, user, project, concept, days_ago=1)
        _add_evidence(db, user, project, concept, days_ago=0)
        assert study_streak_days_global(db, user_id=uid) == 3
        # A gap yesterday kills the run: only day-0 and day-2 remain.
        db.query(MasteryEvidence).filter(MasteryEvidence.user_id == uid).delete(
            synchronize_session=False
        )
        db.commit()
        _add_evidence(db, user, project, concept, days_ago=2)
        _add_evidence(db, user, project, concept, days_ago=0)
        assert study_streak_days_global(db, user_id=uid) == 1
    finally:
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_streak_endpoint_requires_auth_and_returns_count():
    client, engine = _setup()
    try:
        assert client.get("/api/v1/me/streak").status_code == 401
        suffix = uuid.uuid4().hex[:8]
        email = f"stk-e-{suffix}@example.com"
        client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = client.get("/api/v1/me/streak", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json() == {"streak_days": 0}
    finally:
        _teardown(engine)
