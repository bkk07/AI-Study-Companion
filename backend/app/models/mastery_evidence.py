from decimal import Decimal
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class MasteryEvidence(Base, UUIDTimestampMixin):
    """Append-only learning evidence — Phase 40. The Growth Analysis source.

    One row per graded learning action. Writers append; nothing updates or
    deletes rows (no service path does so). `evidence_type` carries the full
    enum now so later phases (mcq, open-ended feeds) insert without migrating.
    `weight` / `resulting_*` mastery columns are deliberately absent — they
    belong to the flagged-open mastery formula, owned by Phase 41.
    """

    __tablename__ = "mastery_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('mcq', 'open_ended', 'explain_back')",
            name="ck_mastery_evidence_type",
        ),
        CheckConstraint("raw_score BETWEEN 0 AND 100", name="ck_mastery_evidence_score"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    raw_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
