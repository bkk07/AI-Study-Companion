"""Relationship reader — Phase B (learning model).

Single place that UNIONs the two edge kinds from design §7:
- hierarchical PART_OF / PARENT_OF / CHILD_OF, derived at read time from the
  existing topic → subtopic → concept FK chain (never stored, never invented);
- semantic edges (PREREQUISITE_OF, RELATED_TO, …) from concept_relationships.
Read-only; Phase C consumers (concept detail, quiz context) build on this.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.concept_relationship import ConceptRelationship
from app.models.subtopic import Subtopic
from app.models.topic import Topic


def get_related(db: Session, concept_id: uuid.UUID) -> dict:
    """Return hierarchy placement + stored semantic edges for one concept.

    Shape: {"concept_id", "part_of": {"topic": {...}, "subtopic": {...}} | None,
    "prerequisites": [...], "related": [...], "outgoing": [...], "incoming": [...]}.
    Raises LookupError for unknown ids. Reads only.
    """
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise LookupError("concept not found")

    part_of = None
    subtopic = db.get(Subtopic, concept.subtopic_id)
    if subtopic is not None:
        topic = db.get(Topic, subtopic.topic_id)
        part_of = {
            "topic": {"id": str(subtopic.topic_id), "title": topic.title if topic else "?"},
            "subtopic": {"id": str(subtopic.id), "title": subtopic.title},
        }

    def _title(cid: uuid.UUID) -> str:
        row = db.get(Concept, cid)
        return row.title if row else "?"

    outgoing = (
        db.query(ConceptRelationship)
        .filter(ConceptRelationship.from_concept_id == concept.id)
        .order_by(ConceptRelationship.created_at.asc())
        .all()
    )
    incoming = (
        db.query(ConceptRelationship)
        .filter(ConceptRelationship.to_concept_id == concept.id)
        .order_by(ConceptRelationship.created_at.asc())
        .all()
    )

    def _edge(r: ConceptRelationship, other_id: uuid.UUID) -> dict:
        return {
            "relation": r.relation,
            "concept_id": str(other_id),
            "title": _title(other_id),
            "evidence_span": r.evidence_span,
            "created_by": r.created_by,
        }

    out_edges = [_edge(r, r.to_concept_id) for r in outgoing]
    in_edges = [_edge(r, r.from_concept_id) for r in incoming]
    return {
        "concept_id": str(concept.id),
        "part_of": part_of,
        "prerequisites": [e for e in in_edges if e["relation"] == "PREREQUISITE_OF"],
        "related": [e for e in out_edges + in_edges if e["relation"] == "RELATED_TO"],
        "outgoing": out_edges,
        "incoming": in_edges,
    }
