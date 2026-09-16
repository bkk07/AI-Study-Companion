"""Phase 41 — mastery engine: confirmed Blueprint EMA over append-only evidence."""

import dataclasses
import inspect
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.mastery_service import (
    EvidenceInput,
    compute_mastery,
    mastery_for_concept,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _pt(score, at=None, difficulty=None, etype="mcq"):
    return EvidenceInput(evidence_type=etype, score=score, difficulty=difficulty, at=at)


def test_bounds_seed_and_empty():
    assert compute_mastery([]).mcq.value is None  # explicit unknown
    assert compute_mastery([]).applied.value is None
    assert compute_mastery([_pt(0), _pt(0)]).mcq.value == pytest.approx(0.0)
    assert compute_mastery([_pt(100), _pt(100)]).mcq.value == pytest.approx(100.0)
    assert compute_mastery([_pt(70)]).mcq.value == pytest.approx(70.0)  # seed = first score
    for bad in (-1, 101, float("nan")):
        with pytest.raises(ValueError):
            EvidenceInput(evidence_type="mcq", score=bad)
    with pytest.raises(ValueError):
        EvidenceInput(evidence_type="mcq", score=True)
    with pytest.raises(ValueError):
        EvidenceInput(evidence_type="vibes", score=50)
    with pytest.raises(ValueError):
        EvidenceInput(evidence_type="mcq", score=50, difficulty="extreme")


def test_stream_independence_and_routing():
    scores = compute_mastery([_pt(100, etype="mcq"), _pt(100, etype="mcq")])
    assert scores.mcq.value == pytest.approx(100.0) and scores.applied.value is None
    scores = compute_mastery([_pt(20, etype="open_ended"), _pt(30, etype="explain_back")])
    assert scores.mcq.value is None
    assert scores.applied.value == pytest.approx(20 + 0.3 * (30 - 20))  # both feed applied
    assert scores.applied.count == 2


def test_difficulty_moves_faster_for_harder():
    easy = compute_mastery([_pt(0), _pt(100, difficulty="easy")]).mcq.value
    hard = compute_mastery([_pt(0), _pt(100, difficulty="hard")]).mcq.value
    assert (easy, hard) == pytest.approx((20.0, 40.0))


def test_gap_boost_and_cap():
    same_day = compute_mastery([_pt(50, at=T0), _pt(100, at=T0, difficulty="medium")]).mcq.value
    assert same_day == pytest.approx(65.0)  # 0.3 base, no boost
    gapped = compute_mastery(
        [_pt(50, at=T0), _pt(100, at=T0 + timedelta(days=10), difficulty="medium")]
    ).mcq.value
    assert gapped == pytest.approx(70.0)  # 0.3 + 0.1 boost
    edge = compute_mastery(
        [_pt(50, at=T0), _pt(100, at=T0 + timedelta(days=7), difficulty="medium")]
    ).mcq.value
    assert edge == pytest.approx(65.0)  # exactly 7d: strictly-exceeds, no boost
    capped = compute_mastery(
        [_pt(50, at=T0), _pt(100, at=T0 + timedelta(days=30), difficulty="hard")]
    ).mcq.value
    assert capped == pytest.approx(75.0)  # 0.4 + 0.1 capped at 0.5


def test_confidence_cannot_reach_the_engine():
    assert {f.name for f in dataclasses.fields(EvidenceInput)} == {"evidence_type", "score", "difficulty", "at"}
    assert list(inspect.signature(compute_mastery).parameters) == ["points"]
    # identical evidence graded with any surrounding confidence yields identical mastery:
    assert compute_mastery([_pt(40), _pt(80)]) == compute_mastery([_pt(40), _pt(80)])


def test_determinism_and_timestamp_ordering():
    pts = [_pt(30, at=T0), _pt(90, at=T0 + timedelta(days=1))]
    assert compute_mastery(pts) == compute_mastery(list(reversed(pts)))  # sorted by time
    with pytest.raises(ValueError):  # mixed present/absent timestamps
        compute_mastery([_pt(30, at=T0), _pt(90)])
    with pytest.raises(ValueError):  # naive + aware mix
        compute_mastery([_pt(30, at=T0), _pt(90, at=datetime(2026, 1, 2))])


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def test_reader_derives_from_rows_and_scopes():
    db = _session()
    try:
        user = User(email=f"me-{uuid.uuid4().hex[:8]}@example.com",
                    hashed_password=hash_password("supersecret123"))
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
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="explain_back", raw_score=40,
                               feedback="Vague.", created_at=T0))
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="explain_back", raw_score=80,
                               feedback="Better.", created_at=T0 + timedelta(days=2)))
        db.commit()
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id, concept_id=concept.id)
        assert scores.applied.value == pytest.approx(40 + 0.3 * 40)  # 2d gap: no boost
        assert scores.applied.count == 2 and scores.applied.last_at == T0 + timedelta(days=2)
        assert scores.mcq.value is None and scores.mcq.count == 0
        with pytest.raises(LookupError):
            mastery_for_concept(db, user_id=user.id, project_id=project.id, concept_id=uuid.uuid4())
    finally:
        db.close()
