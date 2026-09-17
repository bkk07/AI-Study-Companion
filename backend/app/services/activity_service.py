"""Learning events — PRD §12 product-behavior stream (who did what, where, when).

Usage:
    activity_service.record_event(
        db,
        user_id=..., project_id=..., space_id=...,
        event_type=activity_service.EVENT_QUIZ_COMPLETED,
        entity_type="attempt", entity_id=attempt.id,
        payload={"score": 80},
        idempotency_key=f"quiz:{attempt.id}:completed",
    )

Same-session + ON CONFLICT (idempotency_key) DO NOTHING, so retries are
idempotent by construction and events commit atomically with the domain
write they describe. Tracking never breaks the caller: invalid types,
bad FKs, and DB errors are swallowed (False) after rolling back only to
a savepoint — the caller's transaction is never poisoned. Payloads must
stay small (counts/scores/ids); never pass prompt, answer, or document
text.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.learning_event import EVENT_TYPES, LearningEvent

logger = logging.getLogger(__name__)

# Re-export so call sites use one import for types + writer.
from app.models.learning_event import (  # noqa: E402,F401
    EVENT_ASSESSMENT_COMPLETED,
    EVENT_MASTERY_UPDATED,
    EVENT_MATERIAL_FAILED,
    EVENT_MATERIAL_READY,
    EVENT_MATERIAL_UPLOADED,
    EVENT_PROJECT_CREATED,
    EVENT_QUESTION_ANSWERED,
    EVENT_QUIZ_COMPLETED,
    EVENT_QUIZ_STARTED,
    EVENT_RECOMMENDATION_GENERATED,
    EVENT_TUTOR_MESSAGE,
)


def resolve_space_id(db: Session, *, project_id: uuid.UUID) -> uuid.UUID | None:
    """Project → space. None-tolerant by design (tracking never breaks)."""
    try:
        from app.models.project import Project

        project = db.get(Project, project_id)
        return project.space_id if project is not None else None
    except Exception:
        logger.warning("activity space resolution failed", exc_info=True)
        return None


def record_event(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    space_id: uuid.UUID | None,
    event_type: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    payload: dict | None = None,
    idempotency_key: str,
) -> bool:
    """Insert one learning event. Returns True if attempted, False if skipped. Never raises.

    Joins the caller's transaction (flush only, no commit) so the event
    commits atomically with the domain write — or, at post-commit emit
    sites, persists with the caller's follow-up commit. A duplicate key
    is a no-op success (ON CONFLICT DO NOTHING). Failures roll back to a
    savepoint only; the caller's pending writes are never touched.
    """
    if event_type not in EVENT_TYPES:
        logger.warning("activity event rejected: unknown type %r", event_type)
        return False
    if not idempotency_key or not str(idempotency_key).strip():
        logger.warning("activity event rejected: empty idempotency_key")
        return False
    try:
        stmt = (
            pg_insert(LearningEvent)
            .values(
                user_id=user_id,
                project_id=project_id,
                space_id=space_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=dict(payload or {}),
                idempotency_key=str(idempotency_key).strip()[:128],
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
        )
        # Savepoint so a bad row (bad FK, bad type) rolls back only itself —
        # the caller's pending domain writes are untouched. Flush (not
        # commit): the caller's commit persists both atomically.
        with db.begin_nested():
            db.execute(stmt)
            db.flush()
        return True
    except Exception:
        logger.warning("activity event write failed (type=%s)", event_type, exc_info=True)
        return False


def record_event_committed(db: Session, **kwargs) -> bool:
    """record_event + commit for post-commit emit sites. Never raises.

    All current call sites emit after their domain commit, so the event
    needs its own commit to survive session close. The commit only ever
    contains the event row (domain is already durable); on commit failure
    only the event is lost.
    """
    try:
        ok = record_event(db, **kwargs)
        if not ok:
            try:
                db.rollback()
            except Exception:
                pass
            return False
        db.commit()
        return True
    except Exception:
        logger.warning("activity event commit failed", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return False
