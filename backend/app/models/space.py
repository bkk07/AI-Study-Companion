import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDTimestampMixin


class Space(Base, UUIDTimestampMixin):
    """User-owned learning container — Phase 14. Inherited by all nested resources."""

    __tablename__ = "spaces"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # PRD §4: a Space requires a name and description. Nullable so
    # pre-existing rows keep working; new creates should send one.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationship optional for later phases
    # user: Mapped["User"] = relationship("User", back_populates="spaces")
