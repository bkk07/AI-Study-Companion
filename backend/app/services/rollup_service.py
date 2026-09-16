"""Mastery rollups + coverage — Phase C (learning model, design §10).

Presentation layer only: the EMA engine (`mastery_service`) is untouched.
Rules (all from the approved design, implemented verbatim):
- LO display mastery = mean of the LO's known streams; None when neither
  stream has evidence.
- Practiced (per user) = >= 1 evidence row for that (user, LO).
- Rollup = mean of PRACTICED CORE children only; unpracticed CORE objects
  are excluded, never zero. No practiced children → mastery None.
- Coverage = practiced / total CORE children (0/N is valid).
- Obsolete objects are excluded from numerator and denominator.
Full progress drill-down UI is Phase D; browse/detail endpoints (Phase C)
compose on these helpers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.services import mastery_service
from app.services.mastery_levels import is_mastery_target
from app.services.mastery_service import MasteryScores


@dataclass(frozen=True)
class Rollup:
    """Mastery + coverage for one scope. mastery None = "Not started"."""

    mastery: float | None
    practiced: int
    total: int


def display_mastery(scores: MasteryScores) -> float | None:
    """Mean of known streams; None when both streams lack evidence."""
    known = [s.value for s in (scores.mcq, scores.applied) if s.value is not None]
    if not known:
        return None
    return sum(known) / len(known)


def _scope_concepts(concepts: list[Concept]) -> list[Concept]:
    """Mastery-target members of a scope: CORE + non-obsolete."""
    return [c for c in concepts if is_mastery_target(c)]


def rollup_concepts(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, concepts: list[Concept]
) -> Rollup:
    """Roll up an explicit concept list (subtopic/topic/project composers)."""
    members = _scope_concepts(concepts)
    values: list[float] = []
    practiced = 0
    for concept in sorted(members, key=lambda c: str(c.id)):
        scores = mastery_service.mastery_for_concept(
            db, user_id=user_id, project_id=project_id, concept_id=concept.id
        )
        if scores.mcq.count + scores.applied.count > 0:
            practiced += 1
            value = display_mastery(scores)
            if value is not None:
                values.append(value)
    mastery = sum(values) / len(values) if values else None
    return Rollup(mastery=mastery, practiced=practiced, total=len(members))


def rollup_for_subtopic(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, subtopic_id: uuid.UUID
) -> Rollup:
    rows = db.query(Concept).filter(Concept.subtopic_id == subtopic_id).all()
    return rollup_concepts(db, user_id=user_id, project_id=project_id, concepts=rows)


def rollup_for_topic(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, topic_id: uuid.UUID
) -> Rollup:
    sub_ids = [
        s.id for s in db.query(Subtopic).filter(Subtopic.topic_id == topic_id).all()
    ]
    rows = db.query(Concept).filter(Concept.subtopic_id.in_(sub_ids)).all() if sub_ids else []
    return rollup_concepts(db, user_id=user_id, project_id=project_id, concepts=rows)


def rollup_for_project(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID
) -> Rollup:
    rows = db.query(Concept).filter(Concept.project_id == project_id).all()
    return rollup_concepts(db, user_id=user_id, project_id=project_id, concepts=rows)


def topic_ids_for_project(db: Session, project_id: uuid.UUID) -> list[Topic]:
    return (
        db.query(Topic)
        .filter(Topic.project_id == project_id)
        .order_by(Topic.created_at.asc())
        .all()
    )


def subtopics_for_topic(db: Session, topic_id: uuid.UUID) -> list[Subtopic]:
    return (
        db.query(Subtopic)
        .filter(Subtopic.topic_id == topic_id)
        .order_by(Subtopic.created_at.asc())
        .all()
    )
