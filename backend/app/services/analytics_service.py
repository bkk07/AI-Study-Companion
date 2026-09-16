"""Project analytics — read-model aggregates over existing domain data (Phase 46).

Nothing is persisted and no metric is computed twice: counts come from
single `func.count` queries and average mastery is reused from
`growth_service.project_growth` (the one derivation path). Tutor usage is
reported as None — no tutor/message store exists until the later Activity
Events phase, and inventing a counter would violate the read-model guard.
All figures are scoped to (user, project). Reads only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.topic import Topic
from app.services import growth_service

# Material statuses in first-seen order is unstable — fixed display order.
MATERIAL_STATUS_ORDER = ("pending", "processing", "ready", "failed")


@dataclass(frozen=True)
class ProjectAnalytics:
    materials_total: int = 0
    materials_by_status: dict[str, int] = field(default_factory=dict)
    topics_count: int = 0
    concepts_count: int = 0
    quiz_attempts: int = 0
    quiz_attempts_completed: int = 0
    avg_mcq: float | None = None
    avg_applied: float | None = None
    evidenced_concepts: int = 0
    tutor_interactions: None = None  # untracked until the Activity Events phase


def project_analytics(db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID) -> ProjectAnalytics:
    """Aggregate one project's operational stats. Reads only."""
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    materials_total = (
        db.query(func.count(Material.id)).filter(Material.project_id == project.id).scalar() or 0
    )
    status_rows = (
        db.query(Material.status, func.count(Material.id))
        .filter(Material.project_id == project.id)
        .group_by(Material.status)
        .all()
    )
    by_status = {status: count for status, count in status_rows}
    topics_count = db.query(func.count(Topic.id)).filter(Topic.project_id == project.id).scalar() or 0
    concepts_count = (
        db.query(func.count(Concept.id)).filter(Concept.project_id == project.id).scalar() or 0
    )
    attempts_q = (
        db.query(QuizAttempt)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(Quiz.project_id == project.id, QuizAttempt.user_id == user_id)
    )
    attempts = attempts_q.count()
    completed = attempts_q.filter(QuizAttempt.completed_at.is_not(None)).count()
    growth = growth_service.project_growth(db, user_id=user_id, project_id=project.id)
    return ProjectAnalytics(
        materials_total=materials_total,
        materials_by_status={s: by_status.get(s, 0) for s in MATERIAL_STATUS_ORDER if s in by_status},
        topics_count=topics_count,
        concepts_count=concepts_count,
        quiz_attempts=attempts,
        quiz_attempts_completed=completed,
        avg_mcq=growth.avg_mcq,
        avg_applied=growth.avg_applied,
        evidenced_concepts=growth.evidenced_concepts,
    )
