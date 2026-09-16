"""Phase 45 — growth analysis: EMA replay over evidence (real PG)."""

import os
import uuid
from datetime import datetime, timedelta, timezone

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
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.growth_service import concept_growth, project_growth

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
    user = User(email=f"gr-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
    concepts = []
    for title in ("Slope", "Intercept", "Empty"):
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title=title, summary="S.")
        db.add(concept)
        db.flush()
        concepts.append(concept)
    db.commit()
    return user, project, concepts


def _add(db, user_id, project_id, concept_id, etype, score, at):
    db.add(MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                           evidence_type=etype, raw_score=score, created_at=at))
    db.commit()


def test_concept_series_replays_engine():
    db = _session()
    try:
        user, project, (slope, _, _) = _seed(db, uuid.uuid4().hex[:8])
        _add(db, user.id, project.id, slope.id, "explain_back", 40, T0)
        _add(db, user.id, project.id, slope.id, "explain_back", 80, T0 + timedelta(days=2))
        growth = concept_growth(db, user_id=user.id, project_id=project.id, concept_id=slope.id)
        assert growth.count == 2
        assert [p.raw_score for p in growth.points] == [40.0, 80.0]
        assert [p.mcq_after for p in growth.points] == [None, None]  # applied stream only
        assert [p.applied_after for p in growth.points] == pytest.approx([40.0, 52.0])
        assert growth.applied_trend == pytest.approx(12.0) and growth.mcq_trend is None
    finally:
        db.close()


def test_streams_independent_and_empty_honest():
    db = _session()
    try:
        user, project, (slope, _, empty) = _seed(db, uuid.uuid4().hex[:8])
        _add(db, user.id, project.id, slope.id, "mcq", 90, T0)
        _add(db, user.id, project.id, slope.id, "explain_back", 50, T0 + timedelta(days=1))
        growth = concept_growth(db, user_id=user.id, project_id=project.id, concept_id=slope.id)
        assert [(p.mcq_after, p.applied_after) for p in growth.points] == [(90.0, None), (90.0, 50.0)]
        assert growth.mcq_trend is None and growth.applied_trend is None  # <2 per stream
        bare = concept_growth(db, user_id=user.id, project_id=project.id, concept_id=empty.id)
        assert bare.points == () and bare.count == 0
        assert bare.mcq_trend is None and bare.applied_trend is None
        with pytest.raises(LookupError):
            concept_growth(db, user_id=user.id, project_id=project.id, concept_id=uuid.uuid4())
        _, other_project, _ = _seed(db, uuid.uuid4().hex[:8])
        with pytest.raises(LookupError):  # concept from another project
            concept_growth(db, user_id=user.id, project_id=other_project.id, concept_id=slope.id)
    finally:
        db.close()


def test_project_overview_averages_evidenced_only():
    db = _session()
    try:
        user, project, (slope, intercept, _) = _seed(db, uuid.uuid4().hex[:8])
        _add(db, user.id, project.id, slope.id, "mcq", 80, T0)
        _add(db, user.id, project.id, intercept.id, "mcq", 60, T0 + timedelta(days=1))
        overview = project_growth(db, user_id=user.id, project_id=project.id)
        assert overview.evidenced_concepts == 2 and overview.total_evidence == 2  # Empty excluded
        assert overview.avg_mcq == pytest.approx(70.0) and overview.avg_applied is None
        assert [c.title for c in overview.concepts] == ["Slope", "Intercept"]
        assert (overview.since, overview.until) == (T0, T0 + timedelta(days=1))
        with pytest.raises(LookupError):
            project_growth(db, user_id=user.id, project_id=uuid.uuid4())
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


def test_api_shapes_and_isolation():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        headers = {}
        for who in ("a", "b"):
            email = f"grapi-{who}-{suffix}@example.com"
            client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
            resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
            headers[who] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers["a"])
        resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=headers["a"])
        pid = resp.json()["id"]
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            from app.models.user import User as U

            me = db.query(U).filter(U.email == f"grapi-a-{suffix}@example.com").one()
            project = db.get(Project, uuid.UUID(pid))
            topic = Topic(project_id=project.id, title="T")
            db.add(topic)
            db.flush()
            sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
            db.add(sub)
            db.flush()
            concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C", summary="S.")
            db.add(concept)
            db.flush()
            cid = str(concept.id)
            db.add(MasteryEvidence(user_id=me.id, project_id=project.id, concept_id=concept.id,
                                   evidence_type="mcq", raw_score=80, created_at=T0))
            db.commit()
        finally:
            db.close()
        base = f"/api/v1/projects/{pid}/growth"
        overview = client.get(base, headers=headers["a"])
        assert overview.status_code == 200, overview.text
        assert overview.json()["evidenced_concepts"] == 1
        series = client.get(f"{base}?concept_id={cid}", headers=headers["a"])
        assert series.status_code == 200, series.text
        assert series.json()["count"] == 1 and series.json()["mcq_trend"] is None
        assert client.get(f"{base}?concept_id={uuid.uuid4()}", headers=headers["a"]).status_code == 404
        assert client.get(base, headers=headers["b"]).status_code == 404
        assert client.get(base).status_code in (401, 403)
    finally:
        _teardown(engine)
