"""Project analytics — read-model aggregates over existing domain data (Phase 46).

Nothing is persisted and no metric is computed twice: counts come from
single `func.count` queries and average mastery is reused from
`growth_service.project_growth` (the one derivation path). Tutor usage is
the count of user messages in the project's conversations. All figures are
scoped to (user, project). Reads only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.flashcard import Flashcard
from app.models.material import Material
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.topic import Topic
from app.models.tutor_conversation import TutorConversation, TutorMessage
from app.services import growth_service

# Material statuses in first-seen order is unstable — fixed display order.
MATERIAL_STATUS_ORDER = ("pending", "processing", "ready", "failed")


@dataclass(frozen=True)
class ProjectAnalytics:
    materials_total: int = 0
    materials_by_status: dict[str, int] = field(default_factory=dict)
    topics_count: int = 0
    concepts_count: int = 0
    # CORE, non-obsolete practice targets — the same gate as the dashboard,
    # so every "Concepts" figure in the UI agrees. concepts_count keeps the
    # full knowledge-model total (all importances).
    core_concepts_count: int = 0
    quiz_attempts: int = 0
    quiz_attempts_completed: int = 0
    avg_mcq: float | None = None
    avg_applied: float | None = None
    avg_final: float | None = None
    evidenced_concepts: int = 0
    streak_days: int = 0
    tutor_interactions: int = 0


def study_streak_days_global(db: Session, *, user_id: uuid.UUID) -> int:
    """Consecutive UTC days with >= 1 evidence row in ANY project, ending today/yesterday.

    Same clock-skew clamp as the per-project version. Powers the global
    header flame; project pages keep their own scoped streak.
    """
    rows = (
        db.query(func.date(MasteryEvidence.created_at))
        .filter(MasteryEvidence.user_id == user_id)
        .distinct()
        .all()
    )
    today = datetime.now(timezone.utc).date()
    days = sorted({min(r[0], today) for r in rows}, reverse=True)
    if not days or days[0] < today - timedelta(days=1):
        return 0
    streak = 0
    cursor = today
    for day in days:
        if day == cursor:
            streak += 1
            cursor -= timedelta(days=1)
        elif day < cursor:
            break
    return streak


def study_streak_days(db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID) -> int:
    """Consecutive UTC days with >= 1 evidence row, ending today/yesterday.

    Evidence timestamps come from the DB clock, so sub-day skew can yield a
    date one day in the future — clamp to today instead of breaking the run.
    """
    rows = (
        db.query(func.date(MasteryEvidence.created_at))
        .filter(MasteryEvidence.user_id == user_id, MasteryEvidence.project_id == project_id)
        .distinct()
        .all()
    )
    today = datetime.now(timezone.utc).date()
    days = sorted({min(r[0], today) for r in rows}, reverse=True)
    if not days or days[0] < today - timedelta(days=1):
        return 0
    streak = 0
    cursor = today
    for day in days:
        if day == cursor:
            streak += 1
            cursor -= timedelta(days=1)
        elif day < cursor:
            break
    return streak


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
    # Same mastery-target gate as the dashboard (SQL twin + python twin for
    # the obsolete guard), so "Concepts" agrees everywhere.
    from app.services.mastery_levels import is_mastery_target, mastery_target_criterion

    core_candidates = (
        db.query(Concept)
        .filter(Concept.project_id == project.id, mastery_target_criterion())
        .all()
    )
    core_concepts_count = sum(1 for c in core_candidates if is_mastery_target(c))
    tutor_interactions = (
        db.query(func.count(TutorMessage.id))
        .join(TutorConversation, TutorMessage.conversation_id == TutorConversation.id)
        .filter(
            TutorConversation.project_id == project.id,
            TutorConversation.user_id == user_id,
            TutorMessage.role == "user",
        )
        .scalar()
        or 0
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
        materials_by_status={s: by_status.get(s, 0) for s in MATERIAL_STATUS_ORDER},
        topics_count=topics_count,
        concepts_count=concepts_count,
        core_concepts_count=core_concepts_count,
        quiz_attempts=attempts,
        quiz_attempts_completed=completed,
        avg_mcq=growth.avg_mcq,
        avg_applied=growth.avg_applied,
        avg_final=growth.avg_final,
        evidenced_concepts=growth.evidenced_concepts,
        streak_days=study_streak_days(db, user_id=user_id, project_id=project.id),
        tutor_interactions=tutor_interactions,
    )


# ---------------------------------------------------------------------------
# Analytics overview — one read-model for the Analytics page (Figma parity).
#
# Composes ONLY existing derivations (no new formulas, nothing persisted):
# counts are single `func.count` queries, topic/confidence reuse
# `dashboard_service.build_dashboard`, timeline/before-now replay the Plan A
# engine via `mastery_service.compute_mastery` over evidence prefixes.
# Scoped to (user, project). Reads only.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TopicMastery:
    topic: str
    mcq: float | None = None
    applied: float | None = None


@dataclass(frozen=True)
class ConfidencePoint:
    concept_id: uuid.UUID
    concept: str
    confidence: float | None = None
    correctness: float | None = None
    attempts: int = 0
    mismatch_type: str | None = None


@dataclass(frozen=True)
class TimelinePoint:
    date: str
    label: str
    mcq: float | None = None
    applied: float | None = None


@dataclass(frozen=True)
class BeforeNow:
    concept_id: uuid.UUID
    concept: str
    early_mcq: float | None = None
    early_applied: float | None = None
    current_mcq: float | None = None
    current_applied: float | None = None


@dataclass(frozen=True)
class AnalyticsOverview:
    materials_total: int = 0
    concepts_count: int = 0
    core_concepts_count: int = 0
    topics_count: int = 0
    quiz_attempts: int = 0
    quiz_attempts_completed: int = 0
    flashcards_total: int = 0
    tutor_interactions: int = 0
    assessments_total: int = 0
    avg_mcq: float | None = None
    avg_applied: float | None = None
    evidenced_concepts: int = 0
    streak_days: int = 0
    topic_mastery: tuple[TopicMastery, ...] = ()
    confidence_points: tuple[ConfidencePoint, ...] = ()
    timeline: tuple[TimelinePoint, ...] = ()
    before_now: tuple[BeforeNow, ...] = ()


_RANGE_DAYS = {"2w": 14, "1m": 30, "all": None}

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _day_label(day) -> str:
    return f"{_MONTHS[day.month - 1]} {day.day}"


def _avg(values: list[float | None]) -> float | None:
    xs = [v for v in values if v is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def analytics_overview(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, time_range: str = "all"
) -> AnalyticsOverview:
    """Full Analytics-page read-model. Reads only; raises LookupError when missing."""
    from app.services import dashboard_service
    from app.services.mastery_service import EvidenceInput, compute_mastery

    if time_range not in _RANGE_DAYS:
        raise ValueError("time_range must be one of 2w, 1m, all")
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")

    base = project_analytics(db, user_id=user_id, project_id=project.id)

    flashcards_total = (
        db.query(func.count(Flashcard.id)).filter(Flashcard.project_id == project.id).scalar() or 0
    )
    # Tutor count comes from the shared base aggregate (one query, one definition).
    tutor_interactions = base.tutor_interactions
    assessments_total = (
        db.query(func.count(MasteryEvidence.id))
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project.id,
            MasteryEvidence.evidence_type.in_(("open_ended", "explain_back")),
        )
        .scalar()
        or 0
    )

    # Topic mastery + confidence reuse the dashboard composition (one path).
    progress, _ = dashboard_service.build_dashboard(db, user_id=user_id, project_id=project.id)
    by_topic: dict[str, list] = {}
    for p in progress:
        by_topic.setdefault(p.topic, []).append(p)
    topic_mastery = tuple(
        TopicMastery(
            topic=topic,
            mcq=_avg([c.scores.mcq.value for c in items]),
            applied=_avg([c.scores.applied.value for c in items]),
        )
        for topic, items in sorted(by_topic.items())
    )

    confidence_points = tuple(
        ConfidencePoint(
            concept_id=p.concept_id,
            concept=p.title,
            confidence=((p.avg_confidence - 1) / 4 * 100) if p.avg_confidence is not None else None,
            correctness=(p.accuracy * 100) if p.accuracy is not None else None,
            attempts=p.evaluated_count,
            mismatch_type=(p.mismatch.mismatch_type if p.mismatch is not None else None),
        )
        for p in progress
        if p.avg_confidence is not None and p.accuracy is not None
    )

    # Timeline + before/now replay the engine over evidence prefixes.
    rows = (
        db.query(MasteryEvidence)
        .filter(MasteryEvidence.user_id == user_id, MasteryEvidence.project_id == project.id)
        .order_by(MasteryEvidence.created_at.asc())
        .all()
    )

    def _to_input(row: MasteryEvidence) -> EvidenceInput:
        return EvidenceInput(
            evidence_type=row.evidence_type,
            score=float(row.raw_score),
            at=row.created_at,
            source=getattr(row, "source", None),
        )

    timeline: list[TimelinePoint] = []
    before_now: list[BeforeNow] = []
    if rows:
        by_concept: dict[uuid.UUID, list] = {}
        for r in rows:
            by_concept.setdefault(r.concept_id, []).append(r)

        today = datetime.now(timezone.utc).date()
        window = _RANGE_DAYS[time_range]
        cutoff = (today - timedelta(days=window - 1)) if window else None
        days = sorted({r.created_at.date() for r in rows})
        if cutoff is not None:
            days = [d for d in days if d >= cutoff]

        for day in days:
            mcq_vals: list[float | None] = []
            applied_vals: list[float | None] = []
            for _, concept_rows in by_concept.items():
                prefix = [r for r in concept_rows if r.created_at.date() <= day]
                if not prefix:
                    continue
                scores = compute_mastery([_to_input(r) for r in prefix])
                mcq_vals.append(scores.mcq.value)
                applied_vals.append(scores.applied.value)
            timeline.append(
                TimelinePoint(
                    date=day.isoformat(),
                    label=_day_label(day),
                    mcq=_avg(mcq_vals),
                    applied=_avg(applied_vals),
                )
            )

        titles = dict(
            db.query(Concept.id, Concept.title).filter(Concept.project_id == project.id).all()
        )
        ranked: list[tuple[float, BeforeNow]] = []
        for concept_id, concept_rows in by_concept.items():
            if len(concept_rows) < 2:
                continue
            early = compute_mastery([_to_input(concept_rows[0])])
            current = compute_mastery([_to_input(r) for r in concept_rows])
            early_sum = (early.mcq.value or 0) + (early.applied.value or 0)
            current_sum = (current.mcq.value or 0) + (current.applied.value or 0)
            ranked.append(
                (
                    current_sum - early_sum,
                    BeforeNow(
                        concept_id=concept_id,
                        concept=titles.get(concept_id, "Concept"),
                        early_mcq=early.mcq.value,
                        early_applied=early.applied.value,
                        current_mcq=current.mcq.value,
                        current_applied=current.applied.value,
                    ),
                )
            )
        ranked.sort(key=lambda t: t[0], reverse=True)
        before_now = [item for _, item in ranked[:3]]

    return AnalyticsOverview(
        materials_total=base.materials_total,
        concepts_count=base.concepts_count,
        core_concepts_count=base.core_concepts_count,
        topics_count=base.topics_count,
        quiz_attempts=base.quiz_attempts,
        quiz_attempts_completed=base.quiz_attempts_completed,
        flashcards_total=flashcards_total,
        tutor_interactions=tutor_interactions,
        assessments_total=assessments_total,
        avg_mcq=base.avg_mcq,
        avg_applied=base.avg_applied,
        evidenced_concepts=base.evidenced_concepts,
        streak_days=base.streak_days,
        topic_mastery=topic_mastery,
        confidence_points=confidence_points,
        timeline=tuple(timeline),
        before_now=tuple(before_now),
    )
