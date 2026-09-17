from decimal import Decimal
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class MasteryEvidence(Base, UUIDTimestampMixin):
    """Append-only learning evidence — Phase 40. The Growth Analysis source.

    One row per graded learning action. Writers append; nothing updates or
    deletes rows (no service path does so). `evidence_type` carries the
    grading kind (`mcq`, `open_ended`, `explain_back`, `flashcard`, `tutor`);
    `source` carries the Plan A activity stream (`quiz`, `practice`,
    `open_ended`, `flashcard`, `tutor`) and is NULL on legacy rows written
    before the column existed — the mastery engine routes those by
    `evidence_type` (`mcq` → quiz, `open_ended`/`explain_back` → open_ended,
    `flashcard` → flashcard) so old history keeps working unchanged.
    `weight` / `resulting_*` mastery columns are deliberately absent —
    mastery is derived on read by `mastery_service`.
    `difficulty` records the question difficulty (`easy`/`medium`/`hard`) for
    MCQ rows so the engine can weight hard questions more; it is NULL for
    legacy rows and non-MCQ evidence (which keep the default update weight).
    Tutor rows (`evidence_type='tutor'`, `source='tutor'`) come ONLY from a
    graded explain-back/follow-up check via `record_tutor_evidence` (max one
    per day per concept); plain tutor chat messages never write here.
    """

    __tablename__ = "mastery_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('mcq', 'open_ended', 'explain_back', 'flashcard', 'tutor')",
            name="ck_mastery_evidence_type",
        ),
        CheckConstraint(
            "source IS NULL OR source IN ('tutor', 'practice', 'quiz', 'open_ended', 'flashcard')",
            name="ck_mastery_evidence_source",
        ),
        CheckConstraint("raw_score BETWEEN 0 AND 100", name="ck_mastery_evidence_score"),
        CheckConstraint(
            "difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard')",
            name="ck_mastery_evidence_difficulty",
        ),
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
    source: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    raw_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
