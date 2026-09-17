"""Mismatch engine — deterministic divergence detection (Phase 42 + Plan A).

Rule confirmed by the user 2026-09-16 (blueprint §13), not invented:

- Primary: `mcq_mastery - applied_mastery >= 25` with at least 3 mcq and
  at least 1 applied evidence rows → `mcq_high_applied_low`.
- Plan A: `quiz_mastery - open_ended_mastery >= 25` with at least 3 quiz
  and at least 1 open-ended evidence rows → `mcq_high_applied_low`
  ("recognizes the concept but struggles to apply it"). Same badge type —
  no new mismatch kind was invented.
- Secondary (confidence calibration, evaluated records only): average
  confidence >= 4 with accuracy <= 0.5 → `overconfident`; average
  confidence <= 2 with accuracy >= 0.8 → `underconfident`.
- One badge per concept, type priority `mcq_high_applied_low` >
  `overconfident` > `underconfident`; concepts ranked by (type priority,
  gap descending, concept_id ascending) for a stable order.

Pure: no DB, no LLM. Unknown mastery (None) or thin data never flags.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.mismatch import (
    MCQ_HIGH_APPLIED_LOW,
    OVERCONFIDENT,
    TYPE_PRIORITY,
    UNDERCONFIDENT,
    Mismatch,
)

GAP_THRESHOLD = 25.0
MIN_MCQ_EVIDENCE = 3
MIN_APPLIED_EVIDENCE = 1
# Plan A quiz/open-ended rule mirrors the primary minima per stream.
MIN_QUIZ_EVIDENCE = 3
MIN_OPEN_ENDED_EVIDENCE = 1

OVERCONFIDENT_CONF = 4.0
OVERCONFIDENT_ACCURACY = 0.5
UNDERCONFIDENT_CONF = 2.0
UNDERCONFIDENT_ACCURACY = 0.8


@dataclass(frozen=True)
class ConceptState:
    """Current derived state of one concept. Calibration is optional.

    `avg_confidence` (1..5) and `accuracy` (0..1) must be computed over
    evaluated records only — answers still awaiting grading are excluded
    by the caller. `evaluated_count` of 0 (or omitted calibration) means
    no calibration signal, so only the primary rule can fire.

    Plan A stream fields (`quiz_mastery` / `open_ended_mastery` + counts)
    are optional so callers built against the two-stream engine keep
    working; when present they enable the quiz-vs-open-ended gap rule.
    """

    concept_id: uuid.UUID
    mcq_mastery: float | None
    applied_mastery: float | None
    mcq_count: int = 0
    applied_count: int = 0
    avg_confidence: float | None = None
    accuracy: float | None = None
    evaluated_count: int = 0
    quiz_mastery: float | None = None
    open_ended_mastery: float | None = None
    quiz_count: int = 0
    open_ended_count: int = 0

    def __post_init__(self) -> None:
        for name in ("mcq_mastery", "applied_mastery", "quiz_mastery", "open_ended_mastery"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100
            ):
                raise ValueError(f"{name} must be None or 0..100")
        for name in ("mcq_count", "applied_count", "evaluated_count", "quiz_count", "open_ended_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
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


def _calibration_type(state: ConceptState) -> str | None:
    if (
        state.evaluated_count <= 0
        or state.avg_confidence is None
        or state.accuracy is None
    ):
        return None
    if state.avg_confidence >= OVERCONFIDENT_CONF and state.accuracy <= OVERCONFIDENT_ACCURACY:
        return OVERCONFIDENT
    if state.avg_confidence <= UNDERCONFIDENT_CONF and state.accuracy >= UNDERCONFIDENT_ACCURACY:
        return UNDERCONFIDENT
    return None


def _detect_one(state: ConceptState) -> Mismatch | None:
    primary: tuple[float, float, float] | None = None
    if state.mcq_mastery is not None and state.applied_mastery is not None:
        mcq, applied = float(state.mcq_mastery), float(state.applied_mastery)
        if (
            state.mcq_count >= MIN_MCQ_EVIDENCE
            and state.applied_count >= MIN_APPLIED_EVIDENCE
            and mcq - applied >= GAP_THRESHOLD
        ):
            primary = (mcq, applied, mcq - applied)
    # Plan A: high quiz + low open-ended with the same >25 gap semantics.
    # Same badge type — quiz recognition vs applied understanding.
    if state.quiz_mastery is not None and state.open_ended_mastery is not None:
        quiz, opened = float(state.quiz_mastery), float(state.open_ended_mastery)
        if (
            state.quiz_count >= MIN_QUIZ_EVIDENCE
            and state.open_ended_count >= MIN_OPEN_ENDED_EVIDENCE
            and quiz - opened >= GAP_THRESHOLD
        ):
            candidate = (quiz, opened, quiz - opened)
            if primary is None or candidate[2] > primary[2]:
                primary = candidate
    if primary is not None:
        mcq, applied, gap = primary
        reason = (
            f"Recognition looks strong ({mcq:.1f}) but applied understanding "
            f"lags ({applied:.1f}) — a gap of {gap:.1f} points (flags at {GAP_THRESHOLD:.0f})."
        )
        mismatch_type = MCQ_HIGH_APPLIED_LOW
    else:
        # Calibration mismatches keep the original semantics: they require
        # known two-stream mastery (unknown mastery never flags).
        if state.mcq_mastery is None or state.applied_mastery is None:
            return None
        mcq, applied = float(state.mcq_mastery), float(state.applied_mastery)
        gap = mcq - applied
        mismatch_type = _calibration_type(state)
        count = state.evaluated_count
        answers_word = "evaluated answer" if count == 1 else "evaluated answers"
        if mismatch_type == OVERCONFIDENT:
            reason = (
                f"Confidence averages {state.avg_confidence:.1f}/5 but accuracy is "
                f"{state.accuracy * 100:.0f}% over {count} {answers_word}."
            )
        elif mismatch_type == UNDERCONFIDENT:
            reason = (
                f"Accuracy is {state.accuracy * 100:.0f}% but confidence averages only "
                f"{state.avg_confidence:.1f}/5 over {count} {answers_word}."
            )
        else:
            return None
    return Mismatch(
        concept_id=state.concept_id,
        mismatch_type=mismatch_type,
        mcq_mastery=mcq,
        applied_mastery=applied,
        gap=gap,
        reason=reason,
    )


def detect_mismatches(states: list[ConceptState]) -> list[Mismatch]:
    """Flag mismatches across concepts, ranked by type priority then gap."""
    if any(not isinstance(s, ConceptState) for s in states):
        raise ValueError("states must all be ConceptState")
    found = [m for m in (_detect_one(s) for s in states) if m is not None]
    found.sort(key=lambda m: (TYPE_PRIORITY[m.mismatch_type], -m.gap, str(m.concept_id)))
    return found
