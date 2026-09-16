"""Growth analysis — read-time EMA replay over append-only evidence (Phase 45).

No separate engine and no counters: for a scope, order its evidence rows
by `created_at` and re-run the confirmed Phase 41 engine over each
prefix, emitting the running mastery after every point. Concept scope
yields the full series plus per-stream trends (last minus first running
value; None when that stream has fewer than 2 points — sparse histories
are reported honestly, never invented). Project scope aggregates
per-concept current mastery over evidenced concepts only. Read-only,
per-user, no LLM.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.services.mastery_service import EvidenceInput, compute_mastery


@dataclass(frozen=True)
class GrowthPoint:
    at: datetime
    evidence_type: str
    raw_score: float
    mcq_after: float | None
    applied_after: float | None


@dataclass(frozen=True)
class ConceptGrowth:
    concept_id: uuid.UUID
    points: tuple[GrowthPoint, ...] = ()
    mcq_trend: float | None = None
    applied_trend: float | None = None
    count: int = 0


@dataclass(frozen=True)
class ConceptCurrent:
    concept_id: uuid.UUID
    title: str
    mcq: float | None
    applied: float | None
    count: int


@dataclass(frozen=True)
class ProjectGrowth:
    concepts: tuple[ConceptCurrent, ...] = ()
    avg_mcq: float | None = None
    avg_applied: float | None = None
    evidenced_concepts: int = 0
    total_evidence: int = 0
    since: datetime | None = None
    until: datetime | None = None


def _rows(db: Session, user_id: uuid.UUID, project_id: uuid.UUID, concept_id: uuid.UUID):
    return (
        db.query(MasteryEvidence)
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project_id,
            MasteryEvidence.concept_id == concept_id,
        )
        .order_by(MasteryEvidence.created_at.asc())
        .all()
    )


def _check_scope(db: Session, project_id: uuid.UUID, concept_id: uuid.UUID) -> Concept:
    project = db.get(Project, project_id)
    concept = db.get(Concept, concept_id)
    if project is None or concept is None or concept.project_id != project.id:
        raise LookupError("project or concept not found in scope")
    return concept


def _trend(values: list[float]) -> float | None:
    return values[-1] - values[0] if len(values) >= 2 else None


def concept_growth(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, concept_id: uuid.UUID
) -> ConceptGrowth:
    """Replay a concept's evidence into a running-mastery series. Reads only."""
    _check_scope(db, project_id, concept_id)
    rows = _rows(db, user_id, project_id, concept_id)
    seen: list[EvidenceInput] = []
    points: list[GrowthPoint] = []
    mcq_run: list[float] = []
    applied_run: list[float] = []
    for row in rows:
        seen.append(EvidenceInput(evidence_type=row.evidence_type, score=float(row.raw_score), at=row.created_at))
        scores = compute_mastery(seen)
        if row.evidence_type == "mcq":
            mcq_run.append(scores.mcq.value)
        else:
            applied_run.append(scores.applied.value)
        points.append(
            GrowthPoint(
                at=row.created_at,
                evidence_type=row.evidence_type,
                raw_score=float(row.raw_score),
                mcq_after=scores.mcq.value,
                applied_after=scores.applied.value,
            )
        )
    return ConceptGrowth(
        concept_id=concept_id,
        points=tuple(points),
        mcq_trend=_trend(mcq_run),
        applied_trend=_trend(applied_run),
        count=len(points),
    )


def project_growth(db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID) -> ProjectGrowth:
    """Aggregate current mastery over evidenced concepts. Reads only."""
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    concepts = (
        db.query(Concept)
        .filter(Concept.project_id == project.id)
        .order_by(Concept.created_at.asc())
        .all()
    )
    current: list[ConceptCurrent] = []
    stamps: list[datetime] = []
    total = 0
    for concept in concepts:
        rows = _rows(db, user_id, project.id, concept.id)
        if not rows:
            continue  # unevidenced concepts are excluded, never zero-filled
        scores = compute_mastery(
            [EvidenceInput(evidence_type=r.evidence_type, score=float(r.raw_score), at=r.created_at) for r in rows]
        )
        current.append(
            ConceptCurrent(
                concept_id=concept.id,
                title=concept.title,
                mcq=scores.mcq.value,
                applied=scores.applied.value,
                count=len(rows),
            )
        )
        stamps.extend(r.created_at for r in rows)
        total += len(rows)
    mcq_vals = [c.mcq for c in current if c.mcq is not None]
    applied_vals = [c.applied for c in current if c.applied is not None]
    return ProjectGrowth(
        concepts=tuple(current),
        avg_mcq=(sum(mcq_vals) / len(mcq_vals)) if mcq_vals else None,
        avg_applied=(sum(applied_vals) / len(applied_vals)) if applied_vals else None,
        evidenced_concepts=len(current),
        total_evidence=total,
        since=min(stamps) if stamps else None,
        until=max(stamps) if stamps else None,
    )
