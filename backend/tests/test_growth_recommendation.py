"""Growth -> Recommendation closure: growth_service trends feed score_action (real PG).

Flow B: evidence -> mastery -> growth -> recompute -> persisted
recommendation -> dashboard/practice. Growth is ONE deterministic signal
(declining final trend <= -10 -> +15, blueprint S17 boundary) alongside the
unchanged weakness/mismatch/goal/recency/base/repetition signals.
"""

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
from app.models.recommendation import Recommendation
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services import dashboard_service, growth_service, recommendation_service
from app.services.recommendation_service import (
    ConceptSignal,
    recommend,
    score_action,
)

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)
T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _seed(db, suffix, titles=("Slope", "Intercept")):
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
    for title in titles:
        c = Concept(project_id=project.id, subtopic_id=sub.id, title=title, summary="S.")
        db.add(c)
        db.flush()
        concepts.append(c)
    db.commit()
    return user, project, concepts


def _add(db, user_id, project_id, concept_id, etype, score, at, source=None):
    db.add(MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                           evidence_type=etype, source=source, raw_score=score, created_at=at))
    db.commit()


def _sig(name="Slope", mcq=70.0, applied=50.0, **kwargs):
    return ConceptSignal(concept_id=uuid.uuid4(), name=name, mcq=mcq, applied=applied, **kwargs)


# --- 1. growth consumed by scoring ----------------------------------------------

def test_declining_trend_adds_bonus_and_others_untouched():
    base = _sig()
    assert score_action(base, "ask_tutor") == pytest.approx(60.0)
    declining = _sig(growth_trend=-20.0)
    assert score_action(declining, "ask_tutor") == pytest.approx(75.0)  # +15 decline bonus
    assert score_action(_sig(growth_trend=-10.0), "ask_tutor") == pytest.approx(75.0)  # boundary inclusive
    assert score_action(_sig(growth_trend=-9.9), "ask_tutor") == pytest.approx(60.0)  # just above: nothing
    assert score_action(_sig(growth_trend=25.0), "ask_tutor") == pytest.approx(60.0)  # improving: no penalty
    assert score_action(_sig(growth_trend=0.0), "ask_tutor") == pytest.approx(60.0)  # stable: nothing
    assert score_action(_sig(growth_trend=None), "ask_tutor") == pytest.approx(60.0)  # thin: nothing
    with pytest.raises(ValueError):
        _sig(growth_trend=True)


# --- 2. growth changes the winner where expected ----------------------------------

def test_declining_concept_wins_tie_and_reasoning_names_it():
    db = _session()
    try:
        user, project, (slope, intercept) = _seed(db, uuid.uuid4().hex[:8])
        tied_weak = ConceptSignal(concept_id=slope.id, name="Slope", mcq=40.0, applied=40.0,
                                  growth_trend=-25.0)
        tied_flat = ConceptSignal(concept_id=intercept.id, name="Intercept", mcq=40.0, applied=40.0,
                                  growth_trend=2.0)
        row = recommend(db, user_id=user.id, project_id=project.id,
                        signals=[tied_flat, tied_weak], now=NOW)
        assert row.concept_id == slope.id  # growth breaks the weakness tie
        assert "declining" in row.reasoning and "-25.0" in row.reasoning
    finally:
        db.close()


# --- 3. existing signals continue working ------------------------------------------

def test_existing_signals_unchanged_without_growth():
    sig = _sig()
    assert score_action(sig, "ask_tutor") == pytest.approx(60.0)
    assert score_action(sig, "explain_back") == pytest.approx(70.0)
    assert score_action(sig, "review_material") == pytest.approx(55.0)
    assert score_action(_sig(mismatch_type="mcq_high_applied_low"), "explain_back") == pytest.approx(110.0)
    assert score_action(_sig(avg_confidence=4.5, accuracy=0.4, evaluated_count=8),
                        "ask_tutor") == pytest.approx(85.0)
    assert score_action(_sig(days_since_evidence=6.0), "ask_tutor") == pytest.approx(75.0)
    # Growth stacks (does not replace): declining + stale.
    assert score_action(_sig(days_since_evidence=6.0, growth_trend=-30.0),
                        "ask_tutor") == pytest.approx(90.0)


# --- 4+5. persistence + recompute through the real production path -------------------

def test_growth_flows_through_dashboard_recompute_and_persists():
    """Flow B (service level): evidence -> growth trends -> signals -> persisted row."""
    db = _session()
    try:
        user, project, (slope, intercept) = _seed(db, uuid.uuid4().hex[:8])
        # Slope declines hard and stays down (thin-cap-aware: the first
        # running final is capped at 60, so sustain the lows to clear -10).
        for score, day in ((90, 0), (10, 1), (10, 2), (10, 3)):
            _add(db, user.id, project.id, slope.id, "mcq", score, T0 + timedelta(days=day),
                 source="quiz")
        _add(db, user.id, project.id, intercept.id, "mcq", 60, T0, source="quiz")
        _add(db, user.id, project.id, intercept.id, "mcq", 62, T0 + timedelta(days=1), source="quiz")

        trends = growth_service.final_trends_for_project(
            db, user_id=user.id, project_id=project.id)
        assert trends[slope.id] is not None and trends[slope.id] < -10
        assert trends[intercept.id] is not None and trends[intercept.id] > -10

        _, signals = dashboard_service.build_dashboard(db, user_id=user.id, project_id=project.id)
        by_id = {s.concept_id: s for s in signals}
        assert by_id[slope.id].growth_trend == pytest.approx(trends[slope.id])
        assert by_id[intercept.id].growth_trend == pytest.approx(trends[intercept.id])

        row = recommendation_service.recommend(
            db, user_id=user.id, project_id=project.id, signals=signals, now=NOW)
        assert row is not None
        stored = db.query(Recommendation).filter(
            Recommendation.user_id == user.id, Recommendation.project_id == project.id,
            Recommendation.status == "active").all()
        assert len(stored) == 1 and stored[0].id == row.id

        # Thin history (single row) yields None trend and no bonus.
        _, project2, _ = _seed(db, uuid.uuid4().hex[:8])
        assert growth_service.final_trends_for_project(
            db, user_id=user.id, project_id=project2.id) == {}
    finally:
        db.close()


def test_worker_recompute_task_uses_growth():
    from app.worker.tasks.recommendations import generate_recommendation

    db = _session()
    try:
        user, project, (slope, _) = _seed(db, uuid.uuid4().hex[:8])
        for score, day in ((90, 0), (10, 1), (10, 2)):
            _add(db, user.id, project.id, slope.id, "mcq", score, T0 + timedelta(days=day),
                 source="quiz")
        # Call the real Celery task function synchronously (no broker needed).
        row_id = generate_recommendation.run(str(user.id), str(project.id))
        assert row_id is not None
        row = db.get(Recommendation, uuid.UUID(row_id))
        assert row is not None and row.concept_id == slope.id
        assert "declining" in row.reasoning
    finally:
        db.close()


# --- 6. isolation ---------------------------------------------------------------------

def test_growth_recommendation_isolation():
    db = _session()
    try:
        user, project, (slope, _) = _seed(db, uuid.uuid4().hex[:8])
        _, other_project, _ = _seed(db, uuid.uuid4().hex[:8])
        with pytest.raises(LookupError):
            growth_service.final_trends_for_project(
                db, user_id=user.id, project_id=uuid.uuid4())
        foreign = ConceptSignal(concept_id=uuid.uuid4(), name="X", mcq=10.0, applied=10.0,
                                growth_trend=-50.0)
        with pytest.raises(LookupError):
            recommend(db, user_id=user.id, project_id=project.id, signals=[foreign], now=NOW)
    finally:
        db.close()


# --- 7. dashboard / practice APIs -------------------------------------------------------

def _api_setup():
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


def _api_teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def test_dashboard_and_practice_apis_with_growth():
    client, engine = _api_setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        client.post("/api/v1/auth/register", json={"email": f"grapi-{suffix}@example.com",
                                                   "password": "supersecret123"})
        resp = client.post("/api/v1/auth/login", json={"email": f"grapi-{suffix}@example.com",
                                                       "password": "supersecret123"})
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
        pid = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects",
                          json={"name": "P"}, headers=headers).json()["id"]
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            from app.models.user import User as U
            me = db.query(U).filter(U.email == f"grapi-{suffix}@example.com").one()
            project = db.get(Project, uuid.UUID(pid))
            topic = Topic(project_id=project.id, title="T")
            db.add(topic)
            db.flush()
            sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
            db.add(sub)
            db.flush()
            concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="S.")
            db.add(concept)
            db.commit()
            for score, day in ((90, 0), (10, 1), (10, 2), (10, 3)):
                db.add(MasteryEvidence(user_id=me.id, project_id=project.id, concept_id=concept.id,
                                       evidence_type="mcq", source="quiz", raw_score=score,
                                       created_at=T0 + timedelta(days=day)))
            db.commit()
        finally:
            db.close()

        dash = client.get(f"/api/v1/projects/{pid}/dashboard", headers=headers)
        assert dash.status_code == 200, dash.text
        assert dash.json()["concepts"][0]["mcq"] is not None

        refresh = client.post(f"/api/v1/projects/{pid}/dashboard/refresh", headers=headers)
        assert refresh.status_code == 201, refresh.text
        assert "declining" in refresh.json()["reasoning"]

        practice = client.get(f"/api/v1/projects/{pid}/practice/recommendations", headers=headers)
        assert practice.status_code == 200, practice.text
        assert practice.json()["items"]
    finally:
        _api_teardown(engine)
