import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin


class Material(Base, UUIDTimestampMixin):
    """Durable metadata for uploaded learning material — Phase 18. PDF bytes on shared volume, not DB."""

    __tablename__ = "materials"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # Status aligned with background pipeline (Phases 22-23): pending → processing → ready/failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
