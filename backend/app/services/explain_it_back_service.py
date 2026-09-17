"""Explain-It-Back — applied-understanding evidence (Phase 40).

The student explains one concept in their own words; the explanation is
graded with the exact Phase 39 discipline (shared `grade_open_ended` call —
same prompt, same validation, same single retry) and the result is
persisted as an append-only `mastery_evidence` row with
`evidence_type='explain_back'`.

Architecture guard: this service feeds *applied evidence* only. It performs
no mastery recompute and imports no mastery module — that formula is
flagged-open and owned by Phase 41. No endpoints here — see
`app/api/v1/assessment.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.mastery_evidence import MasteryEvidence
from app.services.open_ended_assessment_service import OpenEndedGrade, grade_open_ended


def submit_explanation(
    db: Session,
    *,
    project_id: uuid.UUID,
    concept_id: uuid.UUID,
    user_id: uuid.UUID,
    explanation_text: str,
    client: Callable[[str, str], dict] | None = None,
) -> tuple[MasteryEvidence, OpenEndedGrade]:
    """Grade one explanation and append it as `explain_back` evidence.

    Grading failure persists nothing; the insert is a single commit and any
    insert failure rolls back. Never mutates mastery state.
    Returns the evidence row plus the grade (which carries the verdict).
    """
    grade = grade_open_ended(
        db,
        project_id=project_id,
        concept_id=concept_id,
        answer_text=explanation_text,
        client=client,
    )
    try:
        evidence = MasteryEvidence(
            user_id=user_id,
            project_id=project_id,
            concept_id=concept_id,
            evidence_type="explain_back",
            source="open_ended",
            raw_score=grade.score,
            feedback=grade.feedback,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        # §12: assessment.completed + mastery.updated — one durable grade.
        try:
            from app.services import activity_service

            _space = activity_service.resolve_space_id(db, project_id=project_id)
            activity_service.record_event_committed(
                db,
                user_id=user_id,
                project_id=project_id,
                space_id=_space,
                event_type=activity_service.EVENT_ASSESSMENT_COMPLETED,
                entity_type="evidence",
                entity_id=evidence.id,
                payload={"score": grade.score, "verdict": grade.verdict},
                idempotency_key=f"evidence:{evidence.id}:assessment",
            )
            activity_service.record_event_committed(
                db,
                user_id=user_id,
                project_id=project_id,
                space_id=_space,
                event_type=activity_service.EVENT_MASTERY_UPDATED,
                entity_type="evidence",
                entity_id=evidence.id,
                payload={"evidence_rows": 1, "source": "explain_back"},
                idempotency_key=f"evidence:{evidence.id}:mastery",
            )
        except Exception:
            pass
        # Blueprint §16: recommendation recomputes after mastery-affecting
        # events. Best-effort — evidence is already committed.
        try:
            from app.worker.tasks.recommendations import refresh_best_effort

            refresh_best_effort(user_id, project_id)
        except Exception:
            pass
        return evidence, grade
    except Exception:
        db.rollback()
        raise
