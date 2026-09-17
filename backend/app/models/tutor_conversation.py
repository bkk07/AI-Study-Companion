import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class TutorConversation(Base, UUIDTimestampMixin):
    """One user's chat thread with the tutor inside a project."""

    __tablename__ = "tutor_conversations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New chat")


class TutorMessage(Base, UUIDTimestampMixin):
    """One utterance in a conversation — user question or grounded answer."""

    __tablename__ = "tutor_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_tutor_messages_role"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutor_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Insertion order: created_at ties inside one transaction (statement
    # timestamp), and UUID pks are random — seq is the display order.
    seq: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("nextval('tutor_messages_seq')"), index=True
    )
    supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    follow_ups: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
