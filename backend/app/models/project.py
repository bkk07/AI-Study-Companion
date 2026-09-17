import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class Project(Base, UUIDTimestampMixin):
    """Project parent container — Phase 15. All downstream study data scoped via project_id."""

    __tablename__ = "projects"

    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # PRD §4: a Project carries a description and a learning goal. Nullable
    # so pre-existing rows keep working. `goal` feeds the recommendation
    # engine's goal bonus and the Tutor's project context; `description`
    # is display-only.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
