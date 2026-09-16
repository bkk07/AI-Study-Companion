"""Mastery engine — deterministic EMA over append-only evidence (Phase 41).

Formula confirmed by the user 2026-09-16 (blueprint analysis A1), not invented:
per stream, seed mastery with the first score, then for each later point
`mastery += weight * (score - mastery)`, clamped to 0..100, where
`weight = difficulty base + gap boost`, capped at 0.5:

- difficulty base: easy 0.2 / medium 0.3 / hard 0.4; free-text evidence and
  unknown difficulties default to 0.3,
- gap boost: +0.1 when the gap since the previous evidence in that stream
  strictly exceeds 7 days (relearning after a gap counts more).

Stream routing: `mcq` feeds mcq_mastery; `open_ended` and `explain_back`
feed applied_mastery. A stream with no evidence yields None (explicit
unknown — consumers map it, e.g. adaptive selection already defaults to
neutral 50). Confidence is not an input anywhere in this module: the
mastery/confidence separation is structural.

The engine is pure (no DB, no LLM) plus one thin read-only helper
(`mastery_for_concept`). Nothing here writes: evidence rows are never
mutated, and there is no current-state table — mastery is derived on read.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project

EASY_WEIGHT = 0.2
MEDIUM_WEIGHT = 0.3
HARD_WEIGHT = 0.4
DEFAULT_WEIGHT = 0.3
GAP_BOOST = 0.1
MAX_WEIGHT = 0.5
GAP_THRESHOLD = timedelta(days=7)

MCQ_TYPE = "mcq"
APPLIED_TYPES = frozenset({"open_ended", "explain_back"})
KNOWN_TYPES = frozenset({MCQ_TYPE}) | APPLIED_TYPES
DIFFICULTY_WEIGHTS = {"easy": EASY_WEIGHT, "medium": MEDIUM_WEIGHT, "hard": HARD_WEIGHT}


@dataclass(frozen=True)
class EvidenceInput:
    """One scored evidence point. Note: there is deliberately no confidence field."""

    evidence_type: str
    score: float
    difficulty: str | None = None
    at: datetime | None = None

    def __post_init__(self) -> None:
        if self.evidence_type not in KNOWN_TYPES:
            raise ValueError(f"evidence_type must be one of {sorted(KNOWN_TYPES)}")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ValueError("score must be a number")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be 0..100")
        if self.difficulty is not None and self.difficulty not in DIFFICULTY_WEIGHTS:
            raise ValueError("difficulty must be easy, medium, hard, or None")


@dataclass(frozen=True)
class StreamMastery:
    """Derived state of one stream — value None means no evidence yet."""

    value: float | None
    count: int = 0
    last_at: datetime | None = None


@dataclass(frozen=True)
class MasteryScores:
    mcq: StreamMastery = field(default_factory=StreamMastery)
    applied: StreamMastery = field(default_factory=StreamMastery)


def _weight(difficulty: str | None, gap: timedelta | None) -> float:
    base = DIFFICULTY_WEIGHTS.get(difficulty, DEFAULT_WEIGHT) if difficulty else DEFAULT_WEIGHT
    if gap is not None and gap > GAP_THRESHOLD:
        base += GAP_BOOST
    return min(base, MAX_WEIGHT)


def _run_stream(points: list[EvidenceInput]) -> StreamMastery:
    if not points:
        return StreamMastery(value=None)
    ordered = sorted(points, key=lambda p: p.at) if all(p.at is not None for p in points) else list(points)
    mastery = float(ordered[0].score)
    for prev, cur in zip(ordered, ordered[1:]):
        gap = (cur.at - prev.at) if cur.at is not None and prev.at is not None else None
        mastery += _weight(cur.difficulty, gap) * (float(cur.score) - mastery)
    mastery = min(100.0, max(0.0, mastery))
    last = ordered[-1].at
    return StreamMastery(value=mastery, count=len(ordered), last_at=last)


def compute_mastery(points: list[EvidenceInput]) -> MasteryScores:
    """Derive (mcq, applied) mastery from evidence points. Pure — no I/O."""
    if any(not isinstance(p, EvidenceInput) for p in points):
        raise ValueError("points must all be EvidenceInput")
    ats = [p.at for p in points]
    if any(a is None for a in ats) and any(a is not None for a in ats):
        raise ValueError("timestamps must be all present or all absent")
    if len({(a.tzinfo is None) for a in ats if a is not None}) > 1:
        raise ValueError("timestamps must not mix naive and aware datetimes")
    mcq = [p for p in points if p.evidence_type == MCQ_TYPE]
    applied = [p for p in points if p.evidence_type in APPLIED_TYPES]
    return MasteryScores(mcq=_run_stream(mcq), applied=_run_stream(applied))


def mastery_for_concept(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, concept_id: uuid.UUID
) -> MasteryScores:
    """Read-only derivation for one (user, project, concept). Writes nothing."""
    project = db.get(Project, project_id)
    concept = db.get(Concept, concept_id)
    if project is None or concept is None or concept.project_id != project.id:
        raise LookupError("project or concept not found in scope")
    rows = (
        db.query(MasteryEvidence)
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project.id,
            MasteryEvidence.concept_id == concept.id,
        )
        .order_by(MasteryEvidence.created_at.asc())
        .all()
    )
    return compute_mastery(
        [
            EvidenceInput(evidence_type=r.evidence_type, score=float(r.raw_score), at=r.created_at)
            for r in rows
        ]
    )
