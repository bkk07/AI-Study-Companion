"""Recommendation engine — one explainable current recommendation (Phase 43).

Formula confirmed by the user 2026-09-16 (blueprint §16), not invented.
Per (concept, action):

    score = weakness + uncertainty + recency + goal + base - repetition

- weakness = 100 - min(known masteries),
- uncertainty = +25 when overconfident (avg conf >= 4 with accuracy <= 0.5
  over evaluated records),
- recency = +15 when days since last evidence strictly exceeds 5,
- goal = +10 on a goal-keyword match against the concept name
  (case-insensitive token overlap or phrase substring — e.g. project goal
  "learn gradient descent" matches concept "Gradient Descent"; exact
  whole-name equality is the special case, not the only case),
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

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.concept_relationship import ConceptRelationship
from app.models.project import Project
from app.models.recommendation import Recommendation
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.mismatch import MISMATCH_TYPES
from app.services.mastery_levels import MASTERED_FROM
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


def _tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens of length >= 2 (drops "a"/"of"/punct)."""
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 2}


def _goal_matched(concept_name: str, goal_keywords: tuple[str, ...]) -> bool:
    """True when any goal keyword/phrase matches the concept name.

    Matches on (a) exact whole-name equality (legacy behavior), (b) token
    overlap between keyword tokens and concept-name tokens, or (c) phrase
    substring either direction. All comparisons are case-insensitive.
    Empty/blank keywords never match.
    """
    name = concept_name.strip().lower()
    if not name:
        return False
    name_tokens = _tokenize(concept_name)
    for raw in goal_keywords:
        kw = raw.strip().lower()
        if not kw:
            continue
        if name == kw:
            return True
        if kw in name or name in kw:
            return True
        if name_tokens & _tokenize(raw):
            return True
    return False


def goal_keywords_for_project(project_name: str | None, goal: str | None = None) -> tuple[str, ...]:
    """Derive goal keywords from a project's goal text (falls back to its name).

    No `goal` column existed when this helper was introduced, so the project
    name was the only signal; now the stored learning goal wins when present
    and the name remains the fallback so old projects keep working.
    Returns the raw text plus its tokens so `score_action` can match either
    a whole phrase ("Gradient Descent") or individual words ("gradient").
    Empty/blank input yields () — no bonus, never an error. Callers pass
    `project.goal` first and `project.name` second.
    """
    text = (goal or "").strip() or (project_name or "").strip()
    if not text:
        return ()
    return (text, *sorted(_tokenize(text)))


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
    # Plan A per-stream mastery (optional; scoring still uses the mcq /
    # applied compat aggregates, which already include all five streams).
    quiz: float | None = None
    open_ended: float | None = None
    practice: float | None = None
    flashcard: float | None = None
    tutor: float | None = None
    final: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        for attr in ("mcq", "applied", "quiz", "open_ended", "practice", "flashcard", "tutor", "final"):
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
    goal_hit = _goal_matched(signal.name, goal_keywords)
    if goal_hit:
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


def _explain(
    signal: ConceptSignal,
    action: str,
    score: float,
    times_recommended: int,
    *,
    goal_keywords: tuple[str, ...] = (),
) -> str:
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
    if _goal_matched(signal.name, goal_keywords):
        parts.append("This matches your project goal (+10).")
    parts.append(f"Action base value is {ACTION_BASE[action]:.0f} for {action}.")
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

# Fresh-starter reason template — curriculum-aware, never invented mastery.
FRESH_STARTER_REASON = (
    "No quiz history yet — starting with foundational concepts in curriculum order. "
    "Suggested starting point {position} of {total}: {name}."
)


def _is_practice_eligible(signal: ConceptSignal) -> bool:
    """CORE-only gate for practice lists (None = legacy, reads as CORE)."""
    return signal.importance is None or signal.importance == "CORE"


def _curriculum_order(db: Session, project_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """Curriculum position per concept: Topic → Subtopic → Concept creation order.

    Falls back to empty map on any read problem (caller then uses id order).
    """
    try:
        rows = (
            db.query(Concept.id)
            .join(Subtopic, Concept.subtopic_id == Subtopic.id)
            .join(Topic, Subtopic.topic_id == Topic.id)
            .filter(Concept.project_id == project_id)
            .order_by(Topic.created_at.asc(), Subtopic.created_at.asc(), Concept.created_at.asc())
            .all()
        )
        return {r[0]: i for i, r in enumerate(rows)}
    except Exception:
        return {}


def _prereq_incoming_counts(db: Session, concept_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Count of incoming PREREQUISITE_OF edges per concept (roots == 0)."""
    if not concept_ids:
        return {}
    try:
        rows = (
            db.query(ConceptRelationship.to_concept_id)
            .filter(
                ConceptRelationship.to_concept_id.in_(concept_ids),
                ConceptRelationship.relation == "PREREQUISITE_OF",
            )
            .all()
        )
        counts: dict[uuid.UUID, int] = {}
        for (cid,) in rows:
            counts[cid] = counts.get(cid, 0) + 1
        return counts
    except Exception:
        return {}


def _fresh_sort_key(
    signal: ConceptSignal,
    order: dict[uuid.UUID, int],
    prereqs: dict[uuid.UUID, int],
    goal_keywords: tuple[str, ...],
    total_fresh: int = 0,
) -> tuple:
    """Roots first, then curriculum order, then id. Goal hits float to top."""
    goal_hit = _goal_matched(signal.name, goal_keywords)
    has_prereq = 1 if prereqs.get(signal.concept_id, 0) > 0 else 0
    pos = order.get(signal.concept_id, 10**9)
    return (0 if goal_hit else 1, has_prereq, pos, str(signal.concept_id))


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
    `score_action` engine; returns the top-`limit` plus curriculum-ordered
    fresh starters when nothing has evidence yet. Pure: the `recommendations`
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
    order = _curriculum_order(db, project.id)
    prereqs = _prereq_incoming_counts(db, [s.concept_id for s in eligible])
    ranked: list[PracticeCandidate] = []
    for signal in sorted(eligible, key=lambda s: str(s.concept_id)):
        if signal.mcq is None and signal.applied is None:
            continue
        known = [m for m in (signal.mcq, signal.applied) if m is not None]
        if known and min(float(m) for m in known) >= MASTERED_FROM:
            continue  # mastered: more quizzes add nothing — never top-rank one
        if not is_eligible(TARGETED_QUIZ, evidenced):
            continue
        times = counts.get((signal.concept_id, TARGETED_QUIZ), 0)
        score = score_action(signal, TARGETED_QUIZ, goal_keywords=goal_keywords,
                             times_recommended=times)
        ranked.append(PracticeCandidate(
            signal=signal, score=score,
            reasoning=_explain(signal, TARGETED_QUIZ, score, times, goal_keywords=goal_keywords)))
    # Deterministic tie-break: score desc, then curriculum order, then id
    # (previously bare UUID order — felt random on fresh/close scores).
    ranked.sort(key=lambda c: (-c.score, order.get(c.signal.concept_id, 10**9), str(c.signal.concept_id)))
    ranked = ranked[:limit]
    # Top-up with foundational fresh starters when evidence is thin:
    # fresh projects get curriculum-ordered entry points instead of one
    # random-UUID fallback; partial-evidence projects fill remaining slots.
    fresh = sorted(
        (s for s in eligible if s.mcq is None and s.applied is None),
        key=lambda s: _fresh_sort_key(s, order, prereqs, goal_keywords),
    )
    starters: list[PracticeCandidate] = []
    if fresh:
        slots = limit - len(ranked) if ranked else limit
        for i, sig in enumerate(fresh[:slots]):
            starters.append(PracticeCandidate(
                signal=sig, score=None,
                reasoning=FRESH_STARTER_REASON.format(
                    position=i + 1, total=min(len(fresh), slots), name=sig.name),
                fallback=False))
    if ranked:
        # Evidenced ranking wins; append fresh starters only to fill limit.
        return (ranked + starters)[:limit], None
    if starters:
        # Fresh project: return curriculum-ordered starters as items, no
        # single random fallback. Keeps old single-fallback shape out of the
        # API — callers use items[0] as hero.
        return starters, None
    fallback = None
    if eligible:
        fallback = _review_fallback(eligible)
    return [], fallback


def _review_fallback(eligible: list[ConceptSignal]) -> PracticeCandidate | None:
    """Stalest-mastered review suggestion when every evidenced CORE target is mastered.

    Reason is built from real stored data (mastery value + days since
    evidence) — never invented. Signals without recency sort last; a caller
    with no eligible signals at all gets None (existing 404 path).
    """
    if not eligible:
        return None

    def staleness(signal: ConceptSignal) -> float:
        return signal.days_since_evidence if signal.days_since_evidence is not None else -1.0

    mastered = [
        s for s in eligible
        if s.mcq is not None or s.applied is not None
    ]
    if not mastered:
        return None
    stalest = sorted(mastered, key=lambda s: (-staleness(s), str(s.concept_id)))[0]
    known = [float(m) for m in (stalest.mcq, stalest.applied) if m is not None]
    level = min(known) if known else 0.0
    days = stalest.days_since_evidence
    if days is not None:
        reason = (f"Mastered at {level:.0f}% — {days:.0f} days since practice; "
                  "a quick review keeps it fresh.")
    else:
        reason = f"Mastered at {level:.0f}% — take a review quiz to keep it fresh."
    return PracticeCandidate(signal=stalest, score=None, reasoning=reason, fallback=True)


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
    Mastered concepts (min-known >= MASTERED_FROM) are never served
    TARGETED_QUIZ — more quizzes add nothing there — but stay eligible for
    review/exam/tutor actions, matching `recommend_many`'s quiz-only skip.
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
        known = [m for m in (signal.mcq, signal.applied) if m is not None]
        mastered = bool(known) and min(float(m) for m in known) >= MASTERED_FROM
        for action in ACTIONS:
            if not is_eligible(action, evidenced):
                continue
            if mastered and action == TARGETED_QUIZ:
                continue  # aligned with recommend_many: quizzes never top-rank mastered
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
            reasoning=_explain(signal, action, score, times, goal_keywords=goal_keywords),
            status="active",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        # §12: recommendation.generated — single choke point covers the
        # worker task, dashboard refresh, and direct callers.
        try:
            from app.services import activity_service

            activity_service.record_event_committed(
                db,
                user_id=user_id,
                project_id=project.id,
                space_id=activity_service.resolve_space_id(db, project_id=project.id),
                event_type=activity_service.EVENT_RECOMMENDATION_GENERATED,
                entity_type="recommendation",
                entity_id=row.id,
                payload={"action": action, "score": round(float(score), 2)},
                idempotency_key=f"recommendation:{row.id}",
            )
        except Exception:
            pass
        return row
    except Exception:
        db.rollback()
        raise
