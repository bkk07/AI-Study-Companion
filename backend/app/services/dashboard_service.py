"""Dashboard composition — read-only bridge over derived metrics (Phase 44).

No new formulas here: mastery comes from `mastery_service`, mismatches
from `mismatch_service`, recommendations from `recommendation_service`.
Calibration aggregates rated quiz answers only (confidence present;
accuracy over that same set — one consistent evaluated set for the
mismatch bands; unrated answers are excluded).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.recommendation import Recommendation
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.services import mastery_service, mismatch_service, recommendation_service
from app.services.mastery_levels import is_mastery_target, mastery_target_criterion
from app.services.mastery_service import MasteryScores
from app.services.mismatch_service import ConceptState, Mismatch


@dataclass(frozen=True)
class ConceptProgress:
    concept_id: uuid.UUID
    title: str
    topic: str
    subtopic: str
    scores: MasteryScores
    mismatch: Mismatch | None


def build_dashboard(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, now: datetime | None = None
) -> tuple[list[ConceptProgress], list[recommendation_service.ConceptSignal]]:
    """Compose per-concept progress plus recommendation signals. Reads only."""
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    moment = now or datetime.now(timezone.utc)
    rows = (
        db.query(Concept, Subtopic.title, Topic.title)
        .join(Subtopic, Concept.subtopic_id == Subtopic.id)
        .join(Topic, Subtopic.topic_id == Topic.id)
        .filter(
            Concept.project_id == project.id,
            # Learning-model gate (Phase A): dashboard progress + recommendation
            # signals cover mastery targets only. Behavior-neutral today — every
            # stored row is CORE — and it activates automatically once Phase B
            # writes SUPPORTING/REFERENCE rows. Single-sourced via the helper.
            mastery_target_criterion(),
        )
        .order_by(Topic.created_at.asc(), Subtopic.created_at.asc(), Concept.created_at.asc())
        .all()
    )
    rows = [r for r in rows if is_mastery_target(r[0])]  # python-side twin (obsolete guard)
    states: list[ConceptState] = []
    per_concept: list[tuple[Concept, str, str, MasteryScores, ConceptState, float | None]] = []
    for concept, subtopic_title, topic_title in rows:
        scores = mastery_service.mastery_for_concept(
            db, user_id=user_id, project_id=project.id, concept_id=concept.id
        )
        rated = (
            db.query(QuizAnswer.confidence, QuizAnswer.is_correct)
            .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
            .join(QuizQuestion, QuizAnswer.question_id == QuizQuestion.id)
            .join(Quiz, QuizQuestion.quiz_id == Quiz.id)
            .filter(
                QuizAttempt.user_id == user_id,
                Quiz.project_id == project.id,
                QuizQuestion.concept_id == concept.id,
                QuizAnswer.confidence.is_not(None),
            )
            .all()
        )
        avg_conf = sum(c for c, _ in rated) / len(rated) if rated else None
        accuracy = sum(1 for _, ok in rated if ok) / len(rated) if rated else None
        lasts = [s.last_at for s in (scores.mcq, scores.applied) if s.last_at is not None]
        days = (moment - max(lasts)).total_seconds() / 86400 if lasts else None
        state = ConceptState(
            concept_id=concept.id,
            mcq_mastery=scores.mcq.value,
            applied_mastery=scores.applied.value,
            mcq_count=scores.mcq.count,
            applied_count=scores.applied.count,
            avg_confidence=avg_conf,
            accuracy=accuracy,
            evaluated_count=len(rated),
        )
        states.append(state)
        per_concept.append((concept, topic_title, subtopic_title, scores, state, days))
    mismatches = {m.concept_id: m for m in mismatch_service.detect_mismatches(states)}
    progress = [
        ConceptProgress(
            concept_id=concept.id,
            title=concept.title,
            topic=topic_title,
            subtopic=subtopic_title,
            scores=scores,
            mismatch=mismatches.get(concept.id),
        )
        for concept, topic_title, subtopic_title, scores, _, _ in per_concept
    ]
    signals = [
        recommendation_service.ConceptSignal(
            concept_id=concept.id,
            name=concept.title,
            mcq=scores.mcq.value,
            applied=scores.applied.value,
            mcq_count=scores.mcq.count,
            applied_count=scores.applied.count,
            mismatch_type=(mismatches[concept.id].mismatch_type if concept.id in mismatches else None),
            avg_confidence=state.avg_confidence,
            accuracy=state.accuracy,
            evaluated_count=state.evaluated_count,
            days_since_evidence=days,
        )
        for concept, _, _, scores, state, days in per_concept
    ]
    return progress, signals


def current_recommendation(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID
) -> Recommendation | None:
    """Active row, else the most recent settled one, else None. Reads only."""
    row = (
        db.query(Recommendation)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.project_id == project_id,
            Recommendation.status == "active",
        )
        .order_by(Recommendation.created_at.desc())
        .first()
    )
    if row is not None:
        return row
    return (
        db.query(Recommendation)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.project_id == project_id,
            Recommendation.status.in_(("accepted", "dismissed")),
        )
        .order_by(Recommendation.created_at.desc())
        .first()
    )
