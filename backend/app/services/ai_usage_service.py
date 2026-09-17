"""AI usage tracking — PRD §14 observability (model, feature, latency,
tokens, cost, success/failure).

Usage:
    with track_llm_call(user_id=..., project_id=..., feature=FEATURE_TUTOR_ANSWER):
        parsed = groq_client.chat_json(system, user)

Every provider call inside the block writes one ai_usage row on exit —
including failed calls and retries. Tracking never breaks the caller:
owner resolution is None-tolerant, and rows are written through a
dedicated short-lived session (SessionLocal), so metering survives the
caller's rollback — the tokens were spent even when the request fails —
and can never poison the caller's transaction. No prompt/response text
is ever persisted.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ai_usage import AIUsage
from app.models.project import Project
from app.models.space import Space
from app.services.ai import groq_client
from app.services.ai.pricing import estimate_cost_usd

logger = logging.getLogger(__name__)

# Feature labels — the `feature` column is free-form, but call sites must
# use these constants so admin aggregates stay consistent.
FEATURE_TUTOR_ANSWER = "tutor_answer"
FEATURE_TUTOR_TITLE = "tutor_title"
FEATURE_TUTOR_QUIZ_PLAN = "tutor_quiz_plan"
FEATURE_QUIZ_GENERATION = "quiz_generation"
FEATURE_OPEN_ENDED_GENERATE = "open_ended_generate"
FEATURE_OPEN_ENDED_GRADE = "open_ended_grade"
FEATURE_STRUCTURE_TOPIC_MAP = "structure_topic_map"
FEATURE_STRUCTURE_OBJECTS = "structure_learning_objects"


def resolve_owner_user_id(db: Session, *, project_id: uuid.UUID) -> uuid.UUID | None:
    """Project → space → user. None-tolerant by design."""
    try:
        project = db.get(Project, project_id)
        if project is None:
            return None
        space = db.get(Space, project.space_id)
        return space.user_id if space is not None else None
    except Exception:
        logger.warning("ai_usage owner resolution failed", exc_info=True)
        return None


def resolve_material_owner(
    db: Session, *, material_id: uuid.UUID
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Material → (user_id, project_id). None-tolerant by design."""
    try:
        from app.models.material import Material

        material = db.get(Material, material_id)
        if material is None:
            return None, None
        return resolve_owner_user_id(db, project_id=material.project_id), material.project_id
    except Exception:
        logger.warning("ai_usage material owner resolution failed", exc_info=True)
        return None, None


@contextmanager
def track_llm_call(
    *,
    user_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    feature: str,
    meta: dict | None = None,
) -> Iterator[None]:
    """Meter every provider call in the block into ai_usage. Never raises."""
    records: list[groq_client.LLMCallRecord] = []
    token = groq_client._calls_in_scope.set(records)
    try:
        yield
    finally:
        groq_client._calls_in_scope.reset(token)
        for record in records:
            _persist(record, user_id, project_id, feature, meta)


def _persist(
    record: groq_client.LLMCallRecord,
    user_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    feature: str,
    meta: dict | None,
) -> None:
    try:
        db = SessionLocal()
        try:
            db.add(
                AIUsage(
                    user_id=user_id,
                    project_id=project_id,
                    feature=feature,
                    provider=record.provider,
                    model=record.model,
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    tokens_estimated=record.tokens_estimated,
                    latency_ms=record.latency_ms,
                    success=record.success,
                    error_type=record.error_type,
                    http_status=record.http_status,
                    cost_usd=(
                        estimate_cost_usd(
                            record.model, record.prompt_tokens, record.completion_tokens
                        )
                        if record.success
                        else None
                    ),
                    meta=dict(meta or {}),
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.warning("ai_usage write failed (feature=%s)", feature, exc_info=True)
