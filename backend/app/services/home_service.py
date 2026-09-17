"""Personalized Home read-model — one call answers where / how / what's next (PRD §16).

Read-only composition over existing engines (dashboard, mastery levels,
flashcards, recommendations, analytics streak, learning events). No new
formulas, no LLM calls, no writes. Fan-out is capped (recent projects
only) so one slow project can't sink the page; a project that errors is
skipped, never fatal.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.learning_event import LearningEvent
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.space import Space
from app.services import dashboard_service
from app.services.analytics_service import study_streak_days_global
from app.services.flashcard_service import count_due
from app.services.mastery_levels import MASTERED_FROM

logger = logging.getLogger(__name__)

# continue_ is the field name because `continue` is a Python keyword;
# the API schema exposes it as "continue".
MAX_PROJECTS_SCANNED = 10
MAX_RECENT_PROJECTS = 6
MAX_ATTENTION = 5
MAX_ACTIONS = 5

# Learning event -> project tab to resume in.
EVENT_TABS: tuple[tuple[str, str], ...] = (
    ("tutor.", "tutor"),
    ("quiz.", "quiz"),
    ("question.", "quiz"),
    ("assessment.", "open-ended"),
    ("material.", "materials"),
    ("mastery.", "progress"),
    ("recommendation.", "overview"),
    ("project.", "overview"),
)


def tab_for_event(event_type: str) -> str:
    for prefix, tab in EVENT_TABS:
        if event_type.startswith(prefix):
            return tab
    return "overview"


@dataclass(frozen=True)
class HomeContinue:
    space_id: uuid.UUID
    space_name: str
    project_id: uuid.UUID
    project_name: str
    tab: str
    touched_at: datetime


@dataclass(frozen=True)
class HomeProject:
    id: uuid.UUID
    name: str
    space_id: uuid.UUID
    space_name: str
    progress_pct: float | None
    due_count: int
    attention_count: int
    touched_at: datetime | None


@dataclass(frozen=True)
class HomeAttention:
    project_id: uuid.UUID
    project_name: str
    space_id: uuid.UUID
    concept_id: uuid.UUID
    concept_title: str
    mismatch_type: str
    gap: float | None
    reason: str


@dataclass(frozen=True)
class HomeAction:
    project_id: uuid.UUID
    project_name: str
    space_id: uuid.UUID
    concept_id: uuid.UUID | None
    concept_title: str | None
    action_type: str
    score: float
    reasoning: str
    status: str


@dataclass(frozen=True)
class HomeStats:
    streak_days: int
    due_total: int
    events_week: int
    evidence_total: int


@dataclass(frozen=True)
class HomeDay:
    day: str
    events: int


@dataclass(frozen=True)
class Home:
    continue_: HomeContinue | None = None
    recent_projects: list[HomeProject] = field(default_factory=list)
    stats: HomeStats | None = None
    attention: list[HomeAttention] = field(default_factory=list)
    next_actions: list[HomeAction] = field(default_factory=list)
    week_activity: list[HomeDay] = field(default_factory=list)


def _concept_title(db: Session, concept_id: uuid.UUID | None) -> str | None:
    if concept_id is None:
        return None
    try:
        concept = db.get(Concept, concept_id)
        return concept.title if concept is not None else None
    except Exception:
        logger.warning("home concept lookup failed", exc_info=True)
        return None


def build_home(db: Session, *, user_id: uuid.UUID) -> Home:
    """Compose the personalized Home read-model. Reads only, never raises for data."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    spaces = db.query(Space).filter(Space.user_id == user_id).all()
    space_names = {s.id: s.name for s in spaces}
    space_ids = list(space_names)
    if not space_ids:
        return Home(
            stats=HomeStats(streak_days=0, due_total=0, events_week=0, evidence_total=0),
            week_activity=[
                HomeDay(day=(now - timedelta(days=i)).date().isoformat(), events=0)
                for i in range(6, -1, -1)
            ],
        )

    projects = (
        db.query(Project)
        .filter(Project.space_id.in_(space_ids))
        .order_by(Project.created_at.desc())
        .all()
    )

    # Latest touch per project from the user's own events (drives continue + recency).
    touched_rows = (
        db.query(LearningEvent.project_id, func.max(LearningEvent.created_at))
        .filter(LearningEvent.user_id == user_id, LearningEvent.project_id.is_not(None))
        .group_by(LearningEvent.project_id)
        .all()
    )
    touched = {pid: ts for pid, ts in touched_rows if pid is not None}
    # Touched-first by recency, then untouched by creation order.
    projects.sort(
        key=lambda p: (
            0 if p.id in touched else 1,
            -(touched[p.id].timestamp() if p.id in touched else 0),
        )
    )
    scanned = projects[:MAX_PROJECTS_SCANNED]

    latest = (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == user_id, LearningEvent.project_id.is_not(None))
        .order_by(LearningEvent.created_at.desc())
        .first()
    )
    continue_ = None
    if latest is not None:
        project = db.get(Project, latest.project_id)
        if project is not None and project.space_id in space_names:
            continue_ = HomeContinue(
                space_id=project.space_id,
                space_name=space_names[project.space_id],
                project_id=project.id,
                project_name=project.name,
                tab=tab_for_event(latest.event_type or ""),
                touched_at=latest.created_at,
            )

    recent_projects: list[HomeProject] = []
    attention: list[HomeAttention] = []
    next_actions: list[HomeAction] = []
    due_total = 0
    for project in scanned[:MAX_RECENT_PROJECTS]:
        try:
            progress, _ = dashboard_service.build_dashboard(
                db, user_id=user_id, project_id=project.id
            )
        except Exception:
            logger.warning("home dashboard build failed for project %s", project.id, exc_info=True)
            progress = []
        finals = [p.scores.final for p in progress if p.scores.final is not None]
        pct = round(
            sum(1 for v in finals if float(v) >= MASTERED_FROM) / len(finals) * 100, 1
        ) if finals else None
        try:
            due = count_due(db, project_id=project.id)
        except Exception:
            due = 0
        due_total += due
        mismatches = [p for p in progress if p.mismatch is not None]
        recent_projects.append(
            HomeProject(
                id=project.id,
                name=project.name,
                space_id=project.space_id,
                space_name=space_names.get(project.space_id, ""),
                progress_pct=pct,
                due_count=due,
                attention_count=len(mismatches),
                touched_at=touched.get(project.id),
            )
        )
        for p in mismatches:
            if len(attention) >= MAX_ATTENTION:
                break
            attention.append(
                HomeAttention(
                    project_id=project.id,
                    project_name=project.name,
                    space_id=project.space_id,
                    concept_id=p.concept_id,
                    concept_title=p.title,
                    mismatch_type=p.mismatch.mismatch_type,
                    gap=float(p.mismatch.gap) if p.mismatch.gap is not None else None,
                    reason=p.mismatch.reason,
                )
            )
        try:
            rec = dashboard_service.current_recommendation(
                db, user_id=user_id, project_id=project.id
            )
        except Exception:
            rec = None
        if rec is not None and len(next_actions) < MAX_ACTIONS:
            next_actions.append(
                HomeAction(
                    project_id=project.id,
                    project_name=project.name,
                    space_id=project.space_id,
                    concept_id=rec.concept_id,
                    concept_title=_concept_title(db, rec.concept_id),
                    action_type=rec.action_type,
                    score=float(rec.score),
                    reasoning=rec.reasoning,
                    status=rec.status,
                )
            )

    # Projects beyond the recent window still contribute due counts.
    for project in scanned[MAX_RECENT_PROJECTS:]:
        try:
            due_total += count_due(db, project_id=project.id)
        except Exception:
            continue

    events_week = (
        db.query(func.count(LearningEvent.id))
        .filter(LearningEvent.user_id == user_id, LearningEvent.created_at >= week_ago)
        .scalar()
        or 0
    )
    evidence_total = (
        db.query(func.count(MasteryEvidence.id))
        .filter(MasteryEvidence.user_id == user_id)
        .scalar()
        or 0
    )
    day_rows = (
        db.query(func.date(LearningEvent.created_at), func.count(LearningEvent.id))
        .filter(LearningEvent.user_id == user_id, LearningEvent.created_at >= week_ago)
        .group_by(func.date(LearningEvent.created_at))
        .all()
    )
    by_day = {str(d): c for d, c in day_rows}
    week_activity = [
        HomeDay(
            day=(now - timedelta(days=i)).date().isoformat(),
            events=int(by_day.get((now - timedelta(days=i)).date().isoformat(), 0)),
        )
        for i in range(6, -1, -1)
    ]

    return Home(
        continue_=continue_,
        recent_projects=recent_projects,
        stats=HomeStats(
            streak_days=study_streak_days_global(db, user_id=user_id),
            due_total=due_total,
            events_week=events_week,
            evidence_total=evidence_total,
        ),
        attention=attention,
        next_actions=next_actions,
        week_activity=week_activity,
    )
