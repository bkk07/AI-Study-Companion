import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class AIUsage(Base, UUIDTimestampMixin):
    """One metered LLM call — Phase 50 usage tracking (PRD §14).

    Written best-effort by ai_usage_service.track_llm_call around every
    provider call. Never stores prompt/response text (PII + size) — only
    token counts, latency, model, feature, and outcome, enough to answer
    "which model, why slow, what failed, what did it cost".
    """

    __tablename__ = "ai_usage"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # What product feature spent the call: tutor_answer, quiz_generation, ...
    # (constants in app.services.ai_usage_service). Free-form so new
    # features need no schema change.
    feature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # True when the provider omitted usage and we fell back to len/4.
    tokens_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # No free-text error column by design: exception text can echo
    # prompt/response content, so (error_type, http_status) is all we keep.
    # Estimate at write time (see app.services.ai.pricing); NULL = unknown.
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    # Small retrieval/quality annotations, e.g. tutor chunks + top score.
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
