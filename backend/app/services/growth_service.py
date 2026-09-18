"""Growth analysis — read-time EMA replay over append-only evidence (Phase 45 + Plan A).

No separate engine and no counters: for a scope, order its evidence rows
by `created_at` and re-run the Plan A engine over each prefix, emitting
the running mastery after every point. Concept scope yields the full
series plus per-stream trends (last minus first running value; None when
that stream has fewer than 2 points — sparse histories are reported
honestly, never invented). Project scope aggregates per-concept current
mastery over evidenced concepts only. Read-only, per-user, no LLM.

The legacy `mcq` / `applied` series are preserved verbatim alongside the
five Plan A streams and the weighted `final` series.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.services.mastery_service import EvidenceInput, compute_mastery, stream_for


@dataclass(frozen=True)
class GrowthPoint:
    at: datetime
    evidence_type: str
    raw_score: float
    mcq_after: float | None
    applied_after: float | None
    quiz_after: float | None = None
    open_ended_after: float | None = None
    practice_after: float | None = None
    flashcard_after: float | None = None
    tutor_after: float | None = None
    final_after: float | None = None


@dataclass(frozen=True)
class ConceptGrowth:
    concept_id: uuid.UUID
    points: tuple[GrowthPoint, ...] = ()
    mcq_trend: float | None = None
    applied_trend: float | None = None
    final_trend: float | None = None
    quiz_trend: float | None = None
    open_ended_trend: float | None = None
    practice_trend: float | None = None
    flashcard_trend: float | None = None
    tutor_trend: float | None = None
    count: int = 0


@dataclass(frozen=True)
class ConceptCurrent:
    concept_id: uuid.UUID
    title: str
    mcq: float | None
    applied: float | None
    count: int
    final: float | None = None


@dataclass(frozen=True)
class ProjectGrowth:
    concepts: tuple[ConceptCurrent, ...] = ()
    avg_mcq: float | None = None
    avg_applied: float | None = None
    avg_final: float | None = None
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


def _to_input(row: MasteryEvidence) -> EvidenceInput:
    return EvidenceInput(
        evidence_type=row.evidence_type,
        score=float(row.raw_score),
        at=row.created_at,
        source=getattr(row, "source", None),
    )


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
    final_run: list[float] = []
    stream_runs: dict[str, list[float]] = {
        "quiz": [], "open_ended": [], "practice": [], "flashcard": [], "tutor": [],
    }
    for row in rows:
        seen.append(_to_input(row))
        scores = compute_mastery(seen)
        # Legacy trend membership is by evidence TYPE (unchanged): mcq rows
        # extend the mcq run, everything else the applied run.
        if row.evidence_type == "mcq":
            mcq_run.append(scores.mcq.value)
        else:
            applied_run.append(scores.applied.value)
        route = stream_for(row.evidence_type, getattr(row, "source", None))
        stream_value = getattr(scores, route).value
        if stream_value is not None:
            stream_runs[route].append(stream_value)
        if scores.final is not None:
            final_run.append(scores.final)
        points.append(
            GrowthPoint(
                at=row.created_at,
                evidence_type=row.evidence_type,
                raw_score=float(row.raw_score),
                mcq_after=scores.mcq.value,
                applied_after=scores.applied.value,
                quiz_after=scores.quiz.value,
                open_ended_after=scores.open_ended.value,
                practice_after=scores.practice.value,
                flashcard_after=scores.flashcard.value,
                tutor_after=scores.tutor.value,
                final_after=scores.final,
            )
        )
    return ConceptGrowth(
        concept_id=concept_id,
        points=tuple(points),
        mcq_trend=_trend(mcq_run),
        applied_trend=_trend(applied_run),
        final_trend=_trend(final_run),
        quiz_trend=_trend(stream_runs["quiz"]),
        open_ended_trend=_trend(stream_runs["open_ended"]),
        practice_trend=_trend(stream_runs["practice"]),
        flashcard_trend=_trend(stream_runs["flashcard"]),
        tutor_trend=_trend(stream_runs["tutor"]),
        count=len(points),
    )


def final_trends_from_inputs(
    inputs_by_concept: dict[uuid.UUID, list[EvidenceInput]],
) -> dict[uuid.UUID, float | None]:
    """Per-concept `final` mastery trend from pre-fetched evidence inputs.

    Pure helper so callers that already hold one batched evidence query
    (e.g. ``dashboard_service.build_dashboard``) get growth signals with zero
    extra queries: replay the Plan A engine over each prefix, take the
    running ``final`` series, and return last-minus-first (``None`` when the
    series has fewer than 2 points — sparse histories stay honest, matching
    :func:`concept_growth`). ``growth_service`` remains the single provider
    of growth information; ``recommendation_service`` only consumes it.
    """
    trends: dict[uuid.UUID, float | None] = {}
    for concept_id, points in inputs_by_concept.items():
        run: list[float] = []
        seen: list[EvidenceInput] = []
        for point in points:
            seen.append(point)
            final = compute_mastery(seen).final
            if final is not None:
                run.append(final)
        trends[concept_id] = _trend(run)
    return trends


def final_trends_for_project(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID
) -> dict[uuid.UUID, float | None]:
    """Per-concept `final` trends for one (user, project) in ONE query.

    Same row filter/ordering as the dashboard's batched reader (delegates to
    ``mastery_service.evidence_inputs_by_concept``), then the pure replay
    above. Read-only, per-user, no LLM.
    """
    from app.services.mastery_service import evidence_inputs_by_concept

    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    return final_trends_from_inputs(
        evidence_inputs_by_concept(db, user_id=user_id, project_id=project.id)
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
    # Batch read: one evidence query for the whole project, grouped in memory.
    # Same row filter, ordering, and mapping as the old per-concept reader —
    # identical numbers at ~2 queries total instead of N+1.
    all_rows = (
        db.query(MasteryEvidence)
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project.id,
        )
        .order_by(MasteryEvidence.created_at.asc())
        .all()
    )
    rows_by_concept: dict[uuid.UUID, list[MasteryEvidence]] = {}
    for row in all_rows:
        rows_by_concept.setdefault(row.concept_id, []).append(row)
    for concept in concepts:
        rows = rows_by_concept.get(concept.id, [])
        if not rows:
            continue  # unevidenced concepts are excluded, never zero-filled
        scores = compute_mastery([_to_input(r) for r in rows])
        current.append(
            ConceptCurrent(
                concept_id=concept.id,
                title=concept.title,
                mcq=scores.mcq.value,
                applied=scores.applied.value,
                count=len(rows),
                final=scores.final,
            )
        )
        stamps.extend(r.created_at for r in rows)
        total += len(rows)
    mcq_vals = [c.mcq for c in current if c.mcq is not None]
    applied_vals = [c.applied for c in current if c.applied is not None]
    final_vals = [c.final for c in current if c.final is not None]
    return ProjectGrowth(
        concepts=tuple(current),
        avg_mcq=(sum(mcq_vals) / len(mcq_vals)) if mcq_vals else None,
        avg_applied=(sum(applied_vals) / len(applied_vals)) if applied_vals else None,
        avg_final=(sum(final_vals) / len(final_vals)) if final_vals else None,
        evidenced_concepts=len(current),
        total_evidence=total,
        since=min(stamps) if stamps else None,
        until=max(stamps) if stamps else None,
    )
