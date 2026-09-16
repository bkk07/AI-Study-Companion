import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin

# Local default is BAAI/bge-small-en-v1.5 (384 dims, no key); the OpenAI path
# (text-embedding-3-small, 1536) needs a matching column to be re-enabled.
EMBEDDING_DIMS = 384


class Embedding(Base, UUIDTimestampMixin):
    """One vector per exact chunk — Phase 29. Never stored without chunk scope."""

    __tablename__ = "embeddings"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMS), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="text-embedding-3-small")
