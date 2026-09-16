"""Confidence calibration — independent learning signal (Phase 36/38).

Pure functions over explicit answer records: per-concept accuracy vs
self-reported confidence (1–5) with the calibration gap and the two
decision-relevant extremes (confidently-wrong, unsure-right). Mastery is
deliberately NOT an input — separation is structural, so no future mastery
formula can silently absorb confidence. Storage already exists
(`QuizAnswer.confidence`, captured in Phase 37); no endpoints here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnswerRecord:
    """Minimal calibration fact — correctness plus optional self-report."""

    concept_id: str
    is_correct: bool
    confidence: int | None = None


@dataclass(frozen=True)
class ConceptCalibration:
    concept_id: str
    answered: int = 0
    correct: int = 0
    accuracy: float = 0.0  # correct / answered, correctness-only
    rated: int = 0  # answers carrying a confidence value
    avg_confidence: float | None = None  # 1–5 scale, None when rated == 0
    calibration_gap: float | None = None  # scaled confidence (0–100) minus accuracy pct
    confidently_wrong: int = 0  # wrong with confidence >= 4
    unsure_right: int = 0  # right with confidence <= 2


@dataclass(frozen=True)
class ConfidenceSummary:
    by_concept: dict[str, ConceptCalibration] = field(default_factory=dict)
    overall: ConceptCalibration = ConceptCalibration(concept_id="*")


def _calibrate(concept_id: str, records: list[AnswerRecord]) -> ConceptCalibration:
    answered = len(records)
    if not answered:
        return ConceptCalibration(concept_id=concept_id)
    correct = sum(1 for r in records if r.is_correct)
    rated = [r.confidence for r in records if r.confidence is not None]
    avg = sum(rated) / len(rated) if rated else None
    gap = (avg - 1) * 25 - (correct / answered * 100) if avg is not None else None
    return ConceptCalibration(
        concept_id=concept_id,
        answered=answered,
        correct=correct,
        accuracy=correct / answered,
        rated=len(rated),
        avg_confidence=avg,
        calibration_gap=gap,
        confidently_wrong=sum(1 for r in records if not r.is_correct and (r.confidence or 0) >= 4),
        unsure_right=sum(1 for r in records if r.is_correct and (r.confidence or 6) <= 2),
    )


def summarize(records: list[AnswerRecord]) -> ConfidenceSummary:
    """Roll per-concept and overall calibration from answer records."""
    by_concept: dict[str, list[AnswerRecord]] = {}
    for r in records:
        if r.confidence is not None and not 1 <= r.confidence <= 5:
            raise ValueError(f"confidence must be 1..5, got {r.confidence}")
        by_concept.setdefault(r.concept_id, []).append(r)
    return ConfidenceSummary(
        by_concept={cid: _calibrate(cid, rs) for cid, rs in sorted(by_concept.items())},
        overall=_calibrate("*", records),
    )
