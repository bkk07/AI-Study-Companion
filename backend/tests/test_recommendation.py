"""Phase 43 — recommendation engine: confirmed Blueprint formula (pure + real-PG persist)."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import Concept
from app.models.project import Project
from app.models.recommendation import Recommendation
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.recommendation_service import (
    ConceptSignal,
    is_eligible,
    recommend,
    score_action,
)

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def _sig(name="Slope", mcq=70.0, applied=50.0, **kwargs):
    return ConceptSignal(concept_id=uuid.uuid4(), name=name, mcq=mcq, applied=applied, **kwargs)


def test_base_plus_weakness_math():
    sig = _sig()
    assert score_action(sig, "ask_tutor") == pytest.approx(60.0)  # 50 weakness + 10
    assert score_action(sig, "explain_back") == pytest.approx(70.0)
    assert score_action(sig, "review_material") == pytest.approx(55.0)
    assert score_action(sig, "exam_mode") == pytest.approx(58.0)
    single = ConceptSignal(concept_id=uuid.uuid4(), name="X", mcq=70.0)  # one stream known
    assert score_action(single, "ask_tutor") == pytest.approx(40.0)
    with pytest.raises(ValueError):
        score_action(ConceptSignal(concept_id=uuid.uuid4(), name="X"), "ask_tutor")
    with pytest.raises(ValueError):
        score_action(sig, "nap")


def test_mismatch_pulls_to_applied_practice():
    sig = _sig(mismatch_type="mcq_high_applied_low")
    assert score_action(sig, "explain_back") == pytest.approx(110.0)  # 50 + 20 + 40
    assert score_action(sig, "review_material") == pytest.approx(95.0)
    assert score_action(sig, "targeted_quiz") == pytest.approx(45.0)  # 50 + 15 - 20
    assert score_action(sig, "ask_tutor") == pytest.approx(60.0)  # untouched


def test_uncertainty_recency_goal_and_floor():
    sig = _sig(avg_confidence=4.5, accuracy=0.4, evaluated_count=8)
    assert score_action(sig, "ask_tutor") == pytest.approx(85.0)  # +25 overconfident
    calm = _sig(avg_confidence=3.0, accuracy=0.7, evaluated_count=8)
    assert score_action(calm, "ask_tutor") == pytest.approx(60.0)
    assert score_action(_sig(days_since_evidence=5.0), "ask_tutor") == pytest.approx(60.0)
    assert score_action(_sig(days_since_evidence=6.0), "ask_tutor") == pytest.approx(75.0)
    assert score_action(_sig(), "ask_tutor", goal_keywords=("slope",)) == pytest.approx(70.0)
    assert score_action(_sig(), "ask_tutor", goal_keywords=("Algebra",)) == pytest.approx(60.0)
    weak = _sig(mcq=95.0, applied=95.0)  # weakness 5 + base 10 = 15
    assert score_action(weak, "ask_tutor", times_recommended=3) == 0.0  # floored, never negative
    with pytest.raises(ValueError):
        score_action(_sig(), "ask_tutor", times_recommended=-1)


def test_exam_eligibility_needs_breadth():
    assert is_eligible("exam_mode", 3) is True
    assert is_eligible("exam_mode", 2) is False
    assert is_eligible("ask_tutor", 0) is True
    with pytest.raises(ValueError):
        is_eligible("nap", 9)


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _seed(db, suffix: str):
    user = User(email=f"rec-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
    for title in ("Slope", "Intercept"):
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title=title, summary="S.")
        db.add(concept)
        db.flush()
        concepts.append(concept)
    db.commit()
    return user, project, concepts


def _active(db, user_id, project_id):
    return db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.project_id == project_id,
        Recommendation.status == "active",
    ).all()


def test_recommend_persists_supersedes_and_penalizes():
    db = _session()
    try:
        user, project, (slope, intercept) = _seed(db, uuid.uuid4().hex[:8])
        weak = ConceptSignal(concept_id=slope.id, name="Slope", mcq=40.0, applied=40.0)
        mid = ConceptSignal(concept_id=intercept.id, name="Intercept", mcq=60.0, applied=60.0)
        first = recommend(db, user_id=user.id, project_id=project.id,
                          signals=[weak, mid], now=NOW)
        assert (first.concept_id, first.action_type) == (slope.id, "explain_back")  # 60+20=80 wins
        assert "Slope" in first.reasoning and "40.0" in first.reasoning
        assert len(_active(db, user.id, project.id)) == 1
        second = recommend(db, user_id=user.id, project_id=project.id,
                           signals=[weak, mid], now=NOW)
        # (Slope, explain_back) penalized 25 -> 55; (Slope, targeted_quiz) 75 untouched -> wins:
        assert (second.concept_id, second.action_type) == (slope.id, "targeted_quiz")
        assert "recently" not in second.reasoning  # winner itself was never recommended
        db.refresh(first)
        assert first.status == "expired"
        assert len(_active(db, user.id, project.id)) == 1
    finally:
        db.close()


def test_repetition_window_forgets_old_rows():
    db = _session()
    try:
        user, project, (slope, _) = _seed(db, uuid.uuid4().hex[:8])
        db.add(Recommendation(user_id=user.id, project_id=project.id, concept_id=slope.id,
                              action_type="explain_back", score=80, reasoning="old",
                              status="expired", created_at=NOW - timedelta(days=10)))
        db.commit()
        weak = ConceptSignal(concept_id=slope.id, name="Slope", mcq=40.0, applied=40.0)
        row = recommend(db, user_id=user.id, project_id=project.id, signals=[weak], now=NOW)
        assert row.action_type == "explain_back"  # 10-day-old repeat: no penalty
        assert "recently" not in row.reasoning
    finally:
        db.close()


def test_penalized_winner_names_repetition_in_reasoning():
    db = _session()
    try:
        user, project, (slope, intercept) = _seed(db, uuid.uuid4().hex[:8])
        for action in ("explain_back", "targeted_quiz", "ask_tutor", "review_material"):
            db.add(Recommendation(user_id=user.id, project_id=project.id, concept_id=slope.id,
                                  action_type=action, score=100, reasoning="old",
                                  status="expired", created_at=NOW - timedelta(days=1)))
        db.commit()
        weak = ConceptSignal(concept_id=slope.id, name="Slope", mcq=10.0, applied=10.0)
        mid = ConceptSignal(concept_id=intercept.id, name="Intercept", mcq=60.0, applied=60.0)
        row = recommend(db, user_id=user.id, project_id=project.id,
                        signals=[weak, mid], now=NOW)
        assert (row.concept_id, row.action_type) == (slope.id, "explain_back")  # 110-25=85 still wins
        assert "recently" in row.reasoning
    finally:
        db.close()


def test_recommend_empty_and_scope_guards():
    db = _session()
    try:
        user, project, (slope, _) = _seed(db, uuid.uuid4().hex[:8])
        unknown = ConceptSignal(concept_id=slope.id, name="Slope")  # no mastery: skipped
        assert recommend(db, user_id=user.id, project_id=project.id, signals=[unknown], now=NOW) is None
        assert recommend(db, user_id=user.id, project_id=project.id, signals=[], now=NOW) is None
        assert db.query(Recommendation).filter(Recommendation.project_id == project.id).count() == 0
        foreign = ConceptSignal(concept_id=uuid.uuid4(), name="X", mcq=10.0, applied=10.0)
        with pytest.raises(LookupError):
            recommend(db, user_id=user.id, project_id=project.id, signals=[foreign], now=NOW)
        with pytest.raises(LookupError):
            recommend(db, user_id=user.id, project_id=uuid.uuid4(),
                      signals=[ConceptSignal(concept_id=slope.id, name="S", mcq=1.0)], now=NOW)
        with pytest.raises(ValueError):
            recommend(db, user_id=user.id, project_id=project.id, signals=["nope"], now=NOW)
        assert db.query(Recommendation).filter(Recommendation.project_id == project.id).count() == 0
    finally:
        db.close()
