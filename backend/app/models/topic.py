import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class Topic(Base, UUIDTimestampMixin):
    """Learning topic scoped to a project — Phase 25. Identity is title within project."""

    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("project_id", "title", name="uq_topics_project_title"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
