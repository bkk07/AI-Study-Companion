import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class Flashcard(Base, UUIDTimestampMixin):
    """One reviewable card bound to a learning object — Flashcards v1.

    SM-2 state lives on the row (classic algorithm: 1/6/efactor-scaled
    intervals, 1.30 efactor floor, lapse resets repetitions). Per-review
    history is NOT stored here — each review also banks a `flashcard`
    mastery-evidence row, so history stays in the one append-only place.
    Cards never delete concepts; deleting a concept cascades its cards.
    """

    __tablename__ = "flashcards"
    __table_args__ = (
        UniqueConstraint("concept_id", "front", name="uq_flashcards_concept_front"),
        CheckConstraint("source IN ('auto', 'manual')", name="ck_flashcards_source"),
        CheckConstraint("efactor >= 1.30", name="ck_flashcards_efactor_floor"),
        CheckConstraint("interval_days >= 0", name="ck_flashcards_interval_nonneg"),
        CheckConstraint("repetitions >= 0", name="ck_flashcards_reps_nonneg"),
        Index("ix_flashcards_next_review", "next_review_at"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="auto")
    efactor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("2.50")
    )
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
