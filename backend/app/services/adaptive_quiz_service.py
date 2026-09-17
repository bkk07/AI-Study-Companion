"""Deterministic adaptive question selection — no LLM sequencing (Phase 36).

Confirmed rule (user, 2026-09-16): weakest mastery first, difficulty matched to
mastery (<34 → easy, 34–66 → medium, >66 → hard), exposure-balanced within a
concept (unseen → least-asked → least-recent), all ties by curriculum order
then ID for full determinism. Pure functions over explicit inputs — mastery /
attempt wiring lands with the endpoint and mastery phases; unknown concepts
default to 50.0 neutral. Also exposes concept-level ordering used by quiz
generation so the "adaptive" claim is backed by one shared engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.mastery_levels import DEVELOPING_UPTO, NEEDS_BELOW

DIFFICULTIES = ("easy", "medium", "hard")
MIN_COUNT = 1
MAX_COUNT = 20
UNKNOWN_MASTERY = 50.0


@dataclass(frozen=True)
class CandidateQuestion:
    """One selectable question with the exposure facts the rule needs."""

    question_id: str
    concept_id: str
    difficulty: str
    times_asked: int = 0
    last_asked_at: datetime | None = None


def _target_level(mastery: float) -> int:
    # Bands single-sourced from mastery_levels (audit fix): <34 easy, 34-66
    # medium, >66 hard. Boundary semantics preserved exactly.
    if mastery < NEEDS_BELOW:
        return 0
    if mastery <= DEVELOPING_UPTO:
        return 1
    return 2


def _check_inputs(candidates: list[CandidateQuestion], mastery: dict[str, float], count: int) -> None:
    if not isinstance(count, int) or not MIN_COUNT <= count <= MAX_COUNT:
        raise ValueError(f"count must be {MIN_COUNT}..{MAX_COUNT}")
    for c in candidates:
        if c.difficulty not in DIFFICULTIES:
            raise ValueError(f"unknown difficulty {c.difficulty!r} for question {c.question_id}")
        if c.times_asked < 0:
            raise ValueError(f"times_asked must be >= 0 for question {c.question_id}")
    for concept_id, score in mastery.items():
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ValueError(f"mastery for {concept_id} must be 0..100")


def select_questions(
    candidates: list[CandidateQuestion],
    mastery: dict[str, float],
    count: int,
    curriculum_order: dict[str, int] | None = None,
) -> list[CandidateQuestion]:
    """Pick up to `count` questions, weakest concept first, difficulty-matched."""
    _check_inputs(candidates, mastery, count)
    if not candidates:
        return []
    order = curriculum_order or {}

    by_concept: dict[str, list[CandidateQuestion]] = {}
    for c in candidates:
        by_concept.setdefault(c.concept_id, []).append(c)

    def concept_key(concept_id: str) -> tuple:
        score = mastery.get(concept_id, UNKNOWN_MASTERY)
        exposure = sum(c.times_asked for c in by_concept[concept_id])
        return (score, exposure, order.get(concept_id, 10**9), concept_id)

    ordered_concepts = sorted(by_concept, key=concept_key)

    ranked: dict[str, list[CandidateQuestion]] = {}
    for concept_id in ordered_concepts:
        target = _target_level(mastery.get(concept_id, UNKNOWN_MASTERY))
        ranked[concept_id] = sorted(
            by_concept[concept_id],
            key=lambda c: (
                c.times_asked,
                c.last_asked_at is not None,
                c.last_asked_at,
                abs(DIFFICULTIES.index(c.difficulty) - target),
                c.question_id,
            ),
        )

    picked: list[CandidateQuestion] = []
    while len(picked) < count:
        progressed = False
        for concept_id in ordered_concepts:
            if len(picked) >= count:
                break
            remaining = [c for c in ranked[concept_id] if c not in picked]
            if remaining:
                picked.append(remaining[0])
                progressed = True
        if not progressed:
            break
    return picked


def order_concepts_by_mastery(
    concept_ids: list[str],
    mastery: dict[str, float] | None = None,
    curriculum_order: dict[str, int] | None = None,
    exposure: dict[str, int] | None = None,
) -> list[str]:
    """Shared concept ordering for generation: weakest-first, exposure-aware.

    Used by quiz_generation so selection and generation share one engine
    instead of generation re-inventing round-robin. Unknown mastery defaults
    to 50 neutral; ties break by exposure, curriculum position, then id.
    """
    mastery = mastery or {}
    order = curriculum_order or {}
    exposure = exposure or {}

    def _key(cid: str) -> tuple:
        return (
            mastery.get(cid, UNKNOWN_MASTERY),
            exposure.get(cid, 0),
            order.get(cid, 10**9),
            cid,
        )

    return sorted(concept_ids, key=_key)
