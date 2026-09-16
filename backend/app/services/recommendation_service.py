"""Recommendation engine — one explainable current recommendation (Phase 43).

Formula confirmed by the user 2026-09-16 (blueprint §16), not invented.
Per (concept, action):

    score = weakness + uncertainty + recency + goal + base - repetition

- weakness = 100 - min(known masteries),
- uncertainty = +25 when overconfident (avg conf >= 4 with accuracy <= 0.5
  over evaluated records),
- recency = +15 when days since last evidence strictly exceeds 5,
- goal = +10 on a (case-insensitive) concept-name / goal-keyword match,
- base = ask_tutor 10 / targeted_quiz 15 / explain_back 20 /
  review_material 5 / exam_mode 8,
- repetition = 25 x same (concept, action) recommendations in the last 7 days,
- active mismatch: +40 to explain_back/review_material, -20 to
  targeted_quiz (pull toward applied practice, never more MCQs),
- floored at 0. exam_mode is eligible only with 3+ evidenced concepts.

`score_action` is pure. `recommend` persists: the previous `active` row
for (user, project) is expired so the UI always has exactly one current
recommendation, and the table itself feeds the repetition penalty.
Reasoning names the nonzero drivers with numbers — never LLM-written.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.project import Project
from app.models.recommendation import Recommendation
from app.models.mismatch import MISMATCH_TYPES
from app.services.mismatch_service import OVERCONFIDENT_ACCURACY, OVERCONFIDENT_CONF

ASK_TUTOR = "ask_tutor"
TARGETED_QUIZ = "targeted_quiz"
EXPLAIN_BACK = "explain_back"
REVIEW_MATERIAL = "review_material"
EXAM_MODE = "exam_mode"

ACTIONS = (ASK_TUTOR, TARGETED_QUIZ, EXPLAIN_BACK, REVIEW_MATERIAL, EXAM_MODE)
ACTION_BASE = {
    ASK_TUTOR: 10.0,
    TARGETED_QUIZ: 15.0,
    EXPLAIN_BACK: 20.0,
    REVIEW_MATERIAL: 5.0,
    EXAM_MODE: 8.0,
}

UNCERTAINTY_BONUS = 25.0
RECENCY_BONUS = 15.0
RECENCY_DAYS = 5.0
GOAL_BONUS = 10.0
REPETITION_PENALTY = 25.0
REPETITION_WINDOW = timedelta(days=7)
MISMATCH_APPLIED_BONUS = 40.0
MISMATCH_QUIZ_PENALTY = 20.0
MIN_EVIDENCED_CONCEPTS_FOR_EXAM = 3


@dataclass(frozen=True)
class ConceptSignal:
    """Scorable snapshot of one concept. Unknown mastery is None.

    Calibration fields describe evaluated records only. `mismatch_type`
    comes from `mismatch_service` (None = no active mismatch).
    `importance`/`lo_type` describe the learning object (None = legacy
    caller that predates classification; treated as CORE/CONCEPT).
    """

    concept_id: uuid.UUID
    name: str
    mcq: float | None = None
    applied: float | None = None
    mcq_count: int = 0
    applied_count: int = 0
    mismatch_type: str | None = None
    avg_confidence: float | None = None
    accuracy: float | None = None
    evaluated_count: int = 0
    days_since_evidence: float | None = None
    importance: str | None = None
    lo_type: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        for attr in ("mcq", "applied"):
            value = getattr(self, attr)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100
            ):
                raise ValueError(f"{attr} must be None or 0..100")
        for attr in ("mcq_count", "applied_count", "evaluated_count"):
            value = getattr(self, attr)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{attr} must be a non-negative integer")
        if self.mismatch_type is not None and self.mismatch_type not in MISMATCH_TYPES:
            raise ValueError(f"mismatch_type must be None or one of {MISMATCH_TYPES}")
        if self.avg_confidence is not None and (
            isinstance(self.avg_confidence, bool)
            or not isinstance(self.avg_confidence, (int, float))
            or not 1 <= self.avg_confidence <= 5
        ):
            raise ValueError("avg_confidence must be None or 1..5")
        if self.accuracy is not None and (
            isinstance(self.accuracy, bool)
            or not isinstance(self.accuracy, (int, float))
            or not 0 <= self.accuracy <= 1
        ):
            raise ValueError("accuracy must be None or 0..1")
        if self.days_since_evidence is not None and (
            isinstance(self.days_since_evidence, bool)
            or not isinstance(self.days_since_evidence, (int, float))
            or self.days_since_evidence < 0
        ):
            raise ValueError("days_since_evidence must be None or >= 0")


def _overconfident(signal: ConceptSignal) -> bool:
    return (
        signal.evaluated_count > 0
        and signal.avg_confidence is not None
        and signal.accuracy is not None
        and signal.avg_confidence >= OVERCONFIDENT_CONF
        and signal.accuracy <= OVERCONFIDENT_ACCURACY
    )


def score_action(
    signal: ConceptSignal,
    action: str,
    *,
    goal_keywords: tuple[str, ...] = (),
    times_recommended: int = 0,
) -> float:
    """Deterministic score for one (concept, action) pair. Pure."""
    if action not in ACTION_BASE:
        raise ValueError(f"action must be one of {ACTIONS}")
    if isinstance(times_recommended, bool) or not isinstance(times_recommended, int) or times_recommended < 0:
        raise ValueError("times_recommended must be a non-negative integer")
    known = [m for m in (signal.mcq, signal.applied) if m is not None]
    if not known:
        raise ValueError("signal has no known mastery")
    score = 100.0 - min(float(m) for m in known)
    if _overconfident(signal):
        score += UNCERTAINTY_BONUS
    if signal.days_since_evidence is not None and signal.days_since_evidence > RECENCY_DAYS:
        score += RECENCY_BONUS
    wanted = {k.strip().lower() for k in goal_keywords if k.strip()}
    if signal.name.strip().lower() in wanted:
        score += GOAL_BONUS
    score += ACTION_BASE[action]
    if signal.mismatch_type is not None:
        if action in (EXPLAIN_BACK, REVIEW_MATERIAL):
            score += MISMATCH_APPLIED_BONUS
        elif action == TARGETED_QUIZ:
            score -= MISMATCH_QUIZ_PENALTY
    score -= REPETITION_PENALTY * times_recommended
    return max(0.0, score)


def is_eligible(action: str, evidenced_concepts: int) -> bool:
    """exam_mode needs breadth; every other action is always eligible."""
    if action not in ACTION_BASE:
        raise ValueError(f"action must be one of {ACTIONS}")
    if action == EXAM_MODE:
        return evidenced_concepts >= MIN_EVIDENCED_CONCEPTS_FOR_EXAM
    return True


_ACTION_LEAD = {
    ASK_TUTOR: "Ask the tutor about",
    TARGETED_QUIZ: "Take a targeted quiz on",
    EXPLAIN_BACK: "Explain back",
    REVIEW_MATERIAL: "Review the material for",
    EXAM_MODE: "Run an exam-mode session covering",
}


def _explain(signal: ConceptSignal, action: str, score: float, times_recommended: int) -> str:
    parts = [f"{_ACTION_LEAD[action]} {signal.name} (score {score:.1f})."]
    known = [(label, m) for label, m in (("recognition", signal.mcq), ("applied", signal.applied)) if m is not None]
    parts.append("Mastery is " + " and ".join(f"{label} {m:.1f}" for label, m in known) + ".")
    if signal.mismatch_type is not None:
        if signal.mcq is not None and signal.applied is not None:
            parts.append(
                f"Recognition outruns applied understanding by {signal.mcq - signal.applied:.1f} points, "
                "so applied practice is prioritized over more quizzes."
            )
        else:
            parts.append("An active mismatch flags this concept for applied practice over more quizzes.")
    if _overconfident(signal):
        parts.append(
            f"Confidence averages {signal.avg_confidence:.1f}/5 against "
            f"{signal.accuracy * 100:.0f}% accuracy, so this targets calibration."
        )
    if signal.days_since_evidence is not None and signal.days_since_evidence > RECENCY_DAYS:
        parts.append(f"No evidence for {signal.days_since_evidence:.0f} days, so it is due for review.")
    if times_recommended:
        parts.append(
            f"Recommended {times_recommended} time(s) recently, but it still scores highest."
        )
    return " ".join(parts)


@dataclass(frozen=True)
class PracticeCandidate:
    """One ranked practice target for the Recommended tab (Phase C).

    Pure derivation — nothing persisted. `fallback` marks the neutral
    no-history suggestion ("start with a core concept"), which carries no
    score and no evidence-based reasoning.
    """

    signal: ConceptSignal
    score: float | None
    reasoning: str
    fallback: bool = False


NEUTRAL_FALLBACK_REASON = "Start with a core concept from this topic."
DEFAULT_PRACTICE_LIMIT = 4
MAX_PRACTICE_LIMIT = 8


def _is_practice_eligible(signal: ConceptSignal) -> bool:
    """CORE-only gate for practice lists (None = legacy, reads as CORE)."""
    return signal.importance is None or signal.importance == "CORE"


def recommend_many(
    db: Session,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    signals: list[ConceptSignal],
    limit: int = DEFAULT_PRACTICE_LIMIT,
    goal_keywords: tuple[str, ...] = (),
    now: datetime | None = None,
) -> tuple[list[PracticeCandidate], PracticeCandidate | None]:
    """Rank CORE practice targets without persisting (Phase C, Recommended tab).

    Scores every evidenced CORE signal for TARGETED_QUIZ with the unchanged
    `score_action` engine; returns the top-`limit` plus an optional neutral
    fallback when nothing has evidence yet. Pure: the `recommendations`
    table and the single-active-row contract are untouched.
    """
    if any(not isinstance(s, ConceptSignal) for s in signals):
        raise ValueError("signals must all be ConceptSignal")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    limit = max(1, min(limit, MAX_PRACTICE_LIMIT))
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    owned = {
        c.id
        for c in db.query(Concept.id).filter(Concept.project_id == project.id).all()
    }
    eligible = [s for s in signals if _is_practice_eligible(s)]
    for signal in eligible:
        if signal.concept_id not in owned:
            raise LookupError("concept not found in this project")
    cutoff = (now or datetime.now(timezone.utc)) - REPETITION_WINDOW
    recent = (
        db.query(Recommendation.concept_id, Recommendation.action_type)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.project_id == project.id,
            Recommendation.created_at >= cutoff,
        )
        .all()
    )
    counts: dict[tuple[uuid.UUID, str], int] = {}
    for concept_id, action_type in recent:
        counts[(concept_id, action_type)] = counts.get((concept_id, action_type), 0) + 1
    evidenced = sum(1 for s in eligible if s.mcq_count + s.applied_count > 0)
    ranked: list[PracticeCandidate] = []
    for signal in sorted(eligible, key=lambda s: str(s.concept_id)):
        if signal.mcq is None and signal.applied is None:
            continue
        if not is_eligible(TARGETED_QUIZ, evidenced):
            continue
        times = counts.get((signal.concept_id, TARGETED_QUIZ), 0)
        score = score_action(signal, TARGETED_QUIZ, goal_keywords=goal_keywords,
                             times_recommended=times)
        ranked.append(PracticeCandidate(
            signal=signal, score=score,
            reasoning=_explain(signal, TARGETED_QUIZ, score, times)))
    ranked.sort(key=lambda c: (-c.score, str(c.signal.concept_id)))
    fallback = None
    if not ranked and eligible:
        first = sorted(eligible, key=lambda s: str(s.concept_id))[0]
        fallback = PracticeCandidate(signal=first, score=None,
                                     reasoning=NEUTRAL_FALLBACK_REASON, fallback=True)
    return ranked[:limit], fallback


def recommend(
    db: Session,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    signals: list[ConceptSignal],
    goal_keywords: tuple[str, ...] = (),
    now: datetime | None = None,
) -> Recommendation | None:
    """Score every eligible (concept, action) pair and persist the winner.

    Expires the previous `active` row so exactly one current recommendation
    remains. Returns None (persisting nothing) when no concept is scorable.
    """
    if any(not isinstance(s, ConceptSignal) for s in signals):
        raise ValueError("signals must all be ConceptSignal")
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    owned = {
        c.id
        for c in db.query(Concept.id).filter(Concept.project_id == project.id).all()
    }
    for signal in signals:
        if signal.concept_id not in owned:
            raise LookupError("concept not found in this project")
    moment = now or datetime.now(timezone.utc)
    cutoff = moment - REPETITION_WINDOW
    recent = (
        db.query(Recommendation.concept_id, Recommendation.action_type)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.project_id == project.id,
            Recommendation.created_at >= cutoff,
        )
        .all()
    )
    counts: dict[tuple[uuid.UUID, str], int] = {}
    for concept_id, action_type in recent:
        counts[(concept_id, action_type)] = counts.get((concept_id, action_type), 0) + 1
    evidenced = sum(1 for s in signals if s.mcq_count + s.applied_count > 0)
    ordered = sorted(signals, key=lambda s: str(s.concept_id))
    best: tuple[ConceptSignal, str, float, int] | None = None
    for signal in ordered:
        if signal.mcq is None and signal.applied is None:
            continue
        for action in ACTIONS:
            if not is_eligible(action, evidenced):
                continue
            times = counts.get((signal.concept_id, action), 0)
            score = score_action(signal, action, goal_keywords=goal_keywords, times_recommended=times)
            if best is None or score > best[2]:
                best = (signal, action, score, times)
    if best is None:
        return None
    signal, action, score, times = best
    try:
        db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.project_id == project.id,
            Recommendation.status == "active",
        ).update({"status": "expired"})
        row = Recommendation(
            user_id=user_id,
            project_id=project.id,
            concept_id=signal.concept_id,
            action_type=action,
            score=score,
            reasoning=_explain(signal, action, score, times),
            status="active",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise
