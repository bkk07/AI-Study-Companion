import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class Quiz(Base, UUIDTimestampMixin):
    """Quiz header — Phase 34. Practice/exam modes share one engine (Phase 35+)."""

    __tablename__ = "quizzes"
    __table_args__ = (CheckConstraint("mode IN ('practice', 'exam')", name="ck_quizzes_mode"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class QuizQuestion(Base, UUIDTimestampMixin):
    """One MCQ — evidence stays concept-tied via denormalized concept_id."""

    __tablename__ = "quiz_questions"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_quiz_questions_difficulty"),
    )

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSONB, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=True,
    )
