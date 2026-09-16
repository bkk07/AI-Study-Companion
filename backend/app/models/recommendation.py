import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class Recommendation(Base, UUIDTimestampMixin):
    """Issued recommendation — Phase 43. This table IS the history.

    Unlike mismatch (a read-time derivation), recommendations need
    persistence: the repetition penalty reads recent rows, status
    transitions (accept/dismiss) must stick, and exactly one `active` row
    per (user, project) is the UI's "current recommendation".
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('ask_tutor', 'targeted_quiz', 'explain_back', 'review_material', 'exam_mode')",
            name="ck_recommendations_action",
        ),
        CheckConstraint(
            "status IN ('active', 'accepted', 'dismissed', 'expired')",
            name="ck_recommendations_status",
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
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
