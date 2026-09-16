"""Phase C — recommend_many: CORE-only top-N practice ranking (pure, unpersisted)."""

import os
import uuid

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
from app.services.recommendation_service import (
    NEUTRAL_FALLBACK_REASON,
    ConceptSignal,
    recommend_many,
)


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag):
    user = User(email=f"pr-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
    return user, project, sub


def _concept(db, project, sub, title, importance="CORE", lo_type="CONCEPT"):
    c = Concept(project_id=project.id, subtopic_id=sub.id, title=title,
                summary=f"{title}.", importance=importance, type=lo_type)
    db.add(c)
    db.flush()
    return c


def _sig(concept, mcq=None, applied=None, mcq_count=0, applied_count=0):
    return ConceptSignal(concept_id=concept.id, name=concept.title, mcq=mcq,
                         applied=applied, mcq_count=mcq_count, applied_count=applied_count,
                         importance=concept.importance, lo_type=concept.type)


def test_ranking_weakest_first_with_limit():
    db = _session()
    try:
        user, project, sub = _scaffold(db, uuid.uuid4().hex[:8])
        weak = _concept(db, project, sub, "Weak")
        mid = _concept(db, project, sub, "Mid")
        strong = _concept(db, project, sub, "Strong")
        db.commit()
        signals = [_sig(strong, mcq=90.0, mcq_count=3),
                   _sig(mid, mcq=55.0, mcq_count=2),
                   _sig(weak, mcq=20.0, mcq_count=1)]
        ranked, fallback = recommend_many(db, user_id=user.id, project_id=project.id,
                                          signals=signals, limit=2)
        assert [c.signal.name for c in ranked] == ["Weak", "Mid"]
        assert fallback is None
        assert all(c.score is not None and not c.fallback for c in ranked)
        assert "Weak" in ranked[0].reasoning  # templated, evidence-based reason
        # determinism: same input, same order
        ranked2, _ = recommend_many(db, user_id=user.id, project_id=project.id,
                                    signals=signals, limit=2)
        assert [c.signal.concept_id for c in ranked2] == [c.signal.concept_id for c in ranked]
        # ranking persists nothing
        from app.models.recommendation import Recommendation
        assert db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id).count() == 0
    finally:
        db.close()


def test_non_core_never_ranked_and_legacy_none_included():
    db = _session()
    try:
        user, project, sub = _scaffold(db, uuid.uuid4().hex[:8])
        supp = _concept(db, project, sub, "Supp", importance="SUPPORTING")
        ref = _concept(db, project, sub, "Ref", importance="REFERENCE")
        core = _concept(db, project, sub, "Core")
        db.commit()
        signals = [_sig(supp, mcq=5.0, mcq_count=4),   # weakest, but not practicable
                   _sig(ref, mcq=5.0, mcq_count=4),
                   _sig(core, mcq=80.0, mcq_count=1)]
        ranked, _ = recommend_many(db, user_id=user.id, project_id=project.id, signals=signals)
        assert [c.signal.name for c in ranked] == ["Core"]
        legacy = ConceptSignal(concept_id=core.id, name=core.title, mcq=10.0, mcq_count=1)
        ranked, _ = recommend_many(db, user_id=user.id, project_id=project.id, signals=[legacy])
        assert [c.signal.name for c in ranked] == ["Core"]  # importance None reads as CORE
    finally:
        db.close()


def test_neutral_fallback_without_evidence_and_empty_without_targets():
    db = _session()
    try:
        user, project, sub = _scaffold(db, uuid.uuid4().hex[:8])
        fresh = _concept(db, project, sub, "Fresh")
        db.commit()
        ranked, fallback = recommend_many(
            db, user_id=user.id, project_id=project.id,
            signals=[_sig(fresh)])  # no mastery anywhere
        assert ranked == []
        assert fallback is not None and fallback.fallback is True
        assert fallback.signal.concept_id == fresh.id
        assert fallback.reasoning == NEUTRAL_FALLBACK_REASON
        ranked, fallback = recommend_many(db, user_id=user.id, project_id=project.id, signals=[])
        assert ranked == [] and fallback is None
    finally:
        db.close()


def test_scope_and_input_validation():
    db = _session()
    try:
        user, project, sub = _scaffold(db, uuid.uuid4().hex[:8])
        c = _concept(db, project, sub, "C")
        db.commit()
        with pytest.raises(LookupError):
            recommend_many(db, user_id=user.id, project_id=uuid.uuid4(), signals=[])
        with pytest.raises(LookupError):
            recommend_many(db, user_id=user.id, project_id=project.id,
                           signals=[ConceptSignal(concept_id=uuid.uuid4(), name="X",
                                                  mcq=10.0, mcq_count=1)])
        with pytest.raises(ValueError):
            recommend_many(db, user_id=user.id, project_id=project.id,
                           signals=[{"not": "a signal"}])
        with pytest.raises(ValueError):
            recommend_many(db, user_id=user.id, project_id=project.id,
                           signals=[_sig(c, mcq=10.0, mcq_count=1)], limit=True)
    finally:
        db.close()


def _client():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def test_api_recommendations_and_empty_project_404():
    client, engine = _client()
    try:
        email = f"pra_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        token = client.post("/api/v1/auth/login",
                            json={"email": email, "password": "supersecret123"}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        sid = client.post("/api/v1/spaces", json={"name": "S"}, headers=h).json()["id"]
        pid = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=h).json()["id"]

        resp = client.get(f"/api/v1/projects/{pid}/practice/recommendations", headers=h)
        assert resp.status_code == 404  # no CORE targets yet

        Sess = sessionmaker(bind=engine)
        db = Sess()
        user = db.query(User).filter(User.email == email).one()
        project = db.get(Project, uuid.UUID(pid))
        topic = Topic(project_id=project.id, title="T")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
        db.add(sub)
        db.flush()
        weak = Concept(project_id=project.id, subtopic_id=sub.id, title="Weak", summary="w.")
        strong = Concept(project_id=project.id, subtopic_id=sub.id, title="Strong", summary="s.")
        db.add_all([weak, strong])
        db.flush()
        for cid, score in ((weak.id, 20), (strong.id, 90)):
            db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=cid,
                                   evidence_type="mcq", raw_score=score))
        db.commit()
        db.close()

        resp = client.get(f"/api/v1/projects/{pid}/practice/recommendations?limit=1", headers=h)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert [i["name"] for i in body["items"]] == ["Weak"]
        assert body["items"][0]["status"] == "Needs Practice"
        assert body["fallback"] is None
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
