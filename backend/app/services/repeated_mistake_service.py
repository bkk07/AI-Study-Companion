"""Repeated-mistake workflow — Blueprint §13 (H4).

Identify Pattern → Update Learning Context → Generate Targeted Recommendation.

After each quiz completion, look for concepts the learner keeps missing
(`MIN_WRONG` incorrect answers inside `WINDOW_DAYS`). When one is found and
the current active recommendation does not already target it with applied
practice, expire the active row and persist a targeted `explain_back`
recommendation whose reasoning cites the observed counts — plus a
`mistake.pattern_detected` learning event so the pattern itself stays
queryable in activity/analytics/admin.

Thresholds are judgment calls (the PRD mandates the workflow, not the
numbers): 3 misses in 14 days is strong enough to act on but weak enough
to fire in real use. Deterministic and LLM-free: same answers, same
pattern, same row. Called best-effort from attempt completion — never
raises (evidence is already committed upstream).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.recommendation import Recommendation
from app.services.recommendation_service import EXPLAIN_BACK, REVIEW_MATERIAL

# A concept missed this often inside the window needs applied practice,
# not another quiz.
MIN_WRONG = 3
WINDOW_DAYS = 14

# Active recommendations already giving one of these for the pattern
# concept satisfy the workflow — overriding them would churn, not help.
SATISFYING_ACTIONS = frozenset({EXPLAIN_BACK, REVIEW_MATERIAL})


@dataclass(frozen=True)
class RepeatedMistake:
    """One concept missed repeatedly inside the window (most-missed first)."""

    concept_id: uuid.UUID
    wrong_count: int


def find_repeated_mistakes(
    db: Session,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    now: datetime | None = None,
) -> list[RepeatedMistake]:
    """Concepts with >= MIN_WRONG incorrect answers in the last WINDOW_DAYS.

    Pure read: joins answers → attempts (user) → quizzes (project scope) so
    cross-project answers can never leak in. Ordered most-missed first with
    concept_id ascending as the deterministic tie-break.
    """
    moment = now or datetime.now(timezone.utc)
    cutoff = moment - timedelta(days=WINDOW_DAYS)
    rows = (
        db.query(QuizQuestion.concept_id, func.count(QuizAnswer.id))
        .join(QuizAnswer, QuizAnswer.question_id == QuizQuestion.id)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(
            QuizAttempt.user_id == user_id,
            Quiz.project_id == project_id,
            QuizAnswer.is_correct.is_(False),
            QuizAnswer.answered_at >= cutoff,
            QuizQuestion.concept_id.is_not(None),
        )
        .group_by(QuizQuestion.concept_id)
        .having(func.count(QuizAnswer.id) >= MIN_WRONG)
        .order_by(func.count(QuizAnswer.id).desc(), QuizQuestion.concept_id.asc())
        .all()
    )
    return [RepeatedMistake(concept_id=cid, wrong_count=n) for cid, n in rows]


def target_repeated_mistake(
    db: Session,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    now: datetime | None = None,
) -> Recommendation | None:
    """Persist a targeted recommendation for the worst repeated mistake.

    Returns the active row (newly inserted, or the existing one when it
    already satisfies the pattern), or None when no pattern exists or the
    concept has no scorable signal. Never raises — completion calls this
    best-effort.
    """
    from app.services import activity_service, dashboard_service, recommendation_service

    try:
        patterns = find_repeated_mistakes(db, user_id=user_id, project_id=project_id, now=now)
        if not patterns:
            return None
        pattern = patterns[0]
        concept = db.get(Concept, pattern.concept_id)
        if concept is None or concept.project_id != project_id:
            return None
        current = dashboard_service.current_recommendation(
            db, user_id=user_id, project_id=project_id
        )
        if (
            current is not None
            and current.status == "active"
            and current.concept_id == pattern.concept_id
            and current.action_type in SATISFYING_ACTIONS
        ):
            return current  # already targeted — no churn
        _, signals = dashboard_service.build_dashboard(
            db, user_id=user_id, project_id=project_id
        )
        signal = next((s for s in signals if s.concept_id == pattern.concept_id), None)
        if signal is None or (signal.mcq is None and signal.applied is None):
            return None
        project = db.get(Project, project_id)
        if project is None:
            return None
        goal_keywords = recommendation_service.goal_keywords_for_project(
            project.name, project.goal
        )
        score = recommendation_service.score_action(
            signal, EXPLAIN_BACK, goal_keywords=goal_keywords
        )
        try:
            db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.project_id == project_id,
                Recommendation.status == "active",
            ).update({"status": "expired"})
            row = Recommendation(
                user_id=user_id,
                project_id=project_id,
                concept_id=pattern.concept_id,
                action_type=EXPLAIN_BACK,
                score=score,
                reasoning=(
                    f"Explain back {concept.title} (pattern score {score:.1f}). "
                    f"Missed {pattern.wrong_count} questions in the last "
                    f"{WINDOW_DAYS} days, so applied practice is prioritized "
                    "over more quizzes."
                ),
                status="active",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        except Exception:
            db.rollback()
            return None
        try:
            space_id = activity_service.resolve_space_id(db, project_id=project_id)
            activity_service.record_event_committed(
                db,
                user_id=user_id,
                project_id=project_id,
                space_id=space_id,
                event_type=activity_service.EVENT_MISTAKE_PATTERN,
                entity_type="concept",
                entity_id=pattern.concept_id,
                payload={"wrong_count": pattern.wrong_count, "window_days": WINDOW_DAYS},
                idempotency_key=f"mistake:{pattern.concept_id}:{pattern.wrong_count}",
            )
            activity_service.record_event_committed(
                db,
                user_id=user_id,
                project_id=project_id,
                space_id=space_id,
                event_type=activity_service.EVENT_RECOMMENDATION_GENERATED,
                entity_type="recommendation",
                entity_id=row.id,
                payload={"action": EXPLAIN_BACK, "score": round(float(score), 2)},
                idempotency_key=f"recommendation:{row.id}",
            )
        except Exception:
            pass
        return row
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None
