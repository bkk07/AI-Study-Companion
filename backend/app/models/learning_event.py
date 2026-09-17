import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin

# Product-behavior stream (PRD §12) — who did what, where, when.
# Closed set: callers must use EVENT_* constants in app.services.activity_service.
EVENT_PROJECT_CREATED = "project.created"
EVENT_MATERIAL_UPLOADED = "material.uploaded"
EVENT_MATERIAL_READY = "material.ready"
EVENT_MATERIAL_FAILED = "material.failed"
EVENT_TUTOR_MESSAGE = "tutor.message"
EVENT_QUIZ_STARTED = "quiz.started"
EVENT_QUIZ_COMPLETED = "quiz.completed"
EVENT_QUESTION_ANSWERED = "question.answered"
EVENT_ASSESSMENT_COMPLETED = "assessment.completed"
EVENT_MASTERY_UPDATED = "mastery.updated"
EVENT_RECOMMENDATION_GENERATED = "recommendation.generated"

EVENT_TYPES = (
    EVENT_PROJECT_CREATED,
    EVENT_MATERIAL_UPLOADED,
    EVENT_MATERIAL_READY,
    EVENT_MATERIAL_FAILED,
    EVENT_TUTOR_MESSAGE,
    EVENT_QUIZ_STARTED,
    EVENT_QUIZ_COMPLETED,
    EVENT_QUESTION_ANSWERED,
    EVENT_ASSESSMENT_COMPLETED,
    EVENT_MASTERY_UPDATED,
    EVENT_RECOMMENDATION_GENERATED,
)


class LearningEvent(Base, UUIDTimestampMixin):
    """One product-behavior fact — Phase 2 usage tracking (PRD §12).

    Written best-effort by activity_service.record_event alongside the
    domain write it describes. Same-session + ON CONFLICT DO NOTHING on
    idempotency_key, so Celery/API retries are idempotent by construction.
    Payloads carry small counts/scores only — never prompt, answer, or
    document text (PII + size).
    """

    __tablename__ = "learning_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('project.created', 'material.uploaded', 'material.ready', "
            "'material.failed', 'tutor.message', 'quiz.started', 'quiz.completed', "
            "'question.answered', 'assessment.completed', 'mastery.updated', "
            "'recommendation.generated')",
            name="ck_learning_events_type",
        ),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    space_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Polymorphic ref to the domain row this event describes (no FK by design).
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Small annotations only: scores, counts, ids. Never full text.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Stable per domain action, e.g. f"quiz:{attempt_id}:completed".
    # Unique so retries dedupe; ON CONFLICT DO NOTHING on insert.
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
