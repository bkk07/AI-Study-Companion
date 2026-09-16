"""Mismatch engine — deterministic divergence detection (Phase 42).

Rule confirmed by the user 2026-09-16 (blueprint §13), not invented:

- Primary: `mcq_mastery - applied_mastery >= 25` with at least 3 mcq and
  at least 1 applied evidence rows → `mcq_high_applied_low`.
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
    """

    concept_id: uuid.UUID
    mcq_mastery: float | None
    applied_mastery: float | None
    mcq_count: int = 0
    applied_count: int = 0
    avg_confidence: float | None = None
    accuracy: float | None = None
    evaluated_count: int = 0

    def __post_init__(self) -> None:
        for name in ("mcq_mastery", "applied_mastery"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100
            ):
                raise ValueError(f"{name} must be None or 0..100")
        for name in ("mcq_count", "applied_count", "evaluated_count"):
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
    if state.mcq_mastery is None or state.applied_mastery is None:
        return None  # unknown mastery never flags
    mcq, applied = float(state.mcq_mastery), float(state.applied_mastery)
    gap = mcq - applied
    mismatch_type: str | None = None
    if (
        state.mcq_count >= MIN_MCQ_EVIDENCE
        and state.applied_count >= MIN_APPLIED_EVIDENCE
        and gap >= GAP_THRESHOLD
    ):
        mismatch_type = MCQ_HIGH_APPLIED_LOW
        reason = (
            f"Recognition looks strong ({mcq:.1f}) but applied understanding "
            f"lags ({applied:.1f}) — a gap of {gap:.1f} points (flags at {GAP_THRESHOLD:.0f})."
        )
    else:
        mismatch_type = _calibration_type(state)
        if mismatch_type == OVERCONFIDENT:
            reason = (
                f"Confidence averages {state.avg_confidence:.1f}/5 but accuracy is "
                f"{state.accuracy * 100:.0f}% over {state.evaluated_count} evaluated answers."
            )
        elif mismatch_type == UNDERCONFIDENT:
            reason = (
                f"Accuracy is {state.accuracy * 100:.0f}% but confidence averages only "
                f"{state.avg_confidence:.1f}/5 over {state.evaluated_count} evaluated answers."
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
