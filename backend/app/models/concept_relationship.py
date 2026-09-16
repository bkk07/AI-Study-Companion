import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin

# Semantic edges between learning objects — Phase A (learning model).
# Hierarchical PART_OF/PARENT_OF/CHILD_OF are NOT stored here: they are
# derived at read time from the topic → subtopic → concept FK chain.
# LLM-proposed edges must carry evidence_span ("no evidence → no edge");
# hard caps on edge counts arrive with extraction v2 (Phase B).
RELATIONS = ("PREREQUISITE_OF", "RELATED_TO", "EXAMPLE_OF", "USES", "DERIVED_FROM")
RELATION_CREATORS = ("structure", "llm")


class ConceptRelationship(Base, UUIDTimestampMixin):
    """One directed semantic edge: from_concept RELATION to_concept."""

    __tablename__ = "concept_relationships"
    __table_args__ = (
        UniqueConstraint(
            "from_concept_id", "to_concept_id", "relation",
            name="uq_concept_relationships_triple",
        ),
        CheckConstraint(
            "relation IN ('PREREQUISITE_OF', 'RELATED_TO', 'EXAMPLE_OF', 'USES', 'DERIVED_FROM')",
            name="ck_concept_relationships_relation",
        ),
        CheckConstraint(
            "created_by IN ('structure', 'llm')",
            name="ck_concept_relationships_created_by",
        ),
        CheckConstraint(
            "from_concept_id <> to_concept_id",
            name="ck_concept_relationships_no_self_edge",
        ),
        CheckConstraint(
            "(created_by <> 'llm') OR (evidence_span IS NOT NULL AND evidence_span <> '')",
            name="ck_concept_relationships_llm_evidence",
        ),
        Index("ix_concept_relationships_from", "from_concept_id"),
        Index("ix_concept_relationships_to", "to_concept_id"),
    )

    from_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
