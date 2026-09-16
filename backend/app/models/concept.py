import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin

# Learning-object vocabulary — Phase A (learning model). v1 keeps 7 types;
# new types arrive via a CHECK-extending migration (see design doc §3.3).
# Importance drives routing: CORE → mastery/quiz/progress, everything else
# stays in the knowledge model (RAG/search/context). Legacy NULLs read as
# CONCEPT/CORE (backfilled in migration 9f3a7c1e5b28; readers COALESCE too).
LO_TYPES = ("CONCEPT", "DEFINITION", "TERM", "FORMULA", "PROCESS", "SKILL", "OTHER")
LO_IMPORTANCES = ("CORE", "SUPPORTING", "REFERENCE")
DEFAULT_LO_TYPE = "CONCEPT"
DEFAULT_IMPORTANCE = "CORE"
OBSOLETE_STATUS = "obsolete"  # value of meta["status"] for §9 soft-obsolete (Phase B)


class Concept(Base, UUIDTimestampMixin):
    """Concept scoped to project + parent subtopic — Phase 25. project_id denormalized.

    Phase A adds learning-object semantics: type/importance classification,
    page provenance, material link (SET NULL — deleting a PDF must not
    vaporize history), and extensible metadata. Column `metadata` maps to
    attribute `meta` because `metadata` is reserved by DeclarativeBase.
    """

    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("subtopic_id", "title", name="uq_concepts_subtopic_title"),
        CheckConstraint(
            "type IN ('CONCEPT', 'DEFINITION', 'TERM', 'FORMULA', 'PROCESS', 'SKILL', 'OTHER')",
            name="ck_concepts_lo_type",
        ),
        CheckConstraint(
            "importance IN ('CORE', 'SUPPORTING', 'REFERENCE')",
            name="ck_concepts_importance",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subtopic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subtopics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        Text, nullable=False, default=DEFAULT_LO_TYPE, server_default=DEFAULT_LO_TYPE
    )
    importance: Mapped[str] = mapped_column(
        Text, nullable=False, default=DEFAULT_IMPORTANCE, server_default=DEFAULT_IMPORTANCE,
        index=True,
    )
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    meta: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
