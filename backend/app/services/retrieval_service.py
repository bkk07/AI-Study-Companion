"""Project-scoped semantic retrieval — pure service, no HTTP (Phase 30).

Consumer-neutral foundation for the Phase 31 RAG service: embeds the query
with the same contract as stored chunks and ranks chunks by pgvector cosine
distance. Isolation is enforced inside the SQL query (`project_id`, optional
`concept_id`) — never fetch-all-then-filter in Python. Project ownership
(auth) is the caller's duty; this service enforces the scope filter.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.embedding import EMBEDDING_DIMS, Embedding
from app.services.ai import embedding_client

DEFAULT_TOP_K = 5
MAX_TOP_K = 20


@dataclass(frozen=True)
class RetrievedChunk:
    """One ranked hit with citation metadata for downstream consumers."""

    chunk_id: uuid.UUID
    material_id: uuid.UUID
    content: str
    page_number: int | None
    source_name: str | None
    chunk_index: int
    score: float  # cosine distance — lower means closer


def retrieve(
    db: Session,
    *,
    project_id: uuid.UUID,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    concept_id: uuid.UUID | None = None,
) -> list[RetrievedChunk]:
    """Return the top_k chunks of a project ranked by query similarity.

    Raises:
        ValueError: on empty query or embedding-dimension mismatch.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    top_k = max(1, min(int(top_k), MAX_TOP_K))

    # Short-circuit before spending an embedding call: a scope with no stored
    # vectors cannot rank anything (and an empty project must answer
    # unsupported without requiring the AI provider to be reachable).
    scope = (
        db.query(Embedding.id)
        .join(DocumentChunk, DocumentChunk.id == Embedding.chunk_id)
        .filter(Embedding.project_id == project_id, DocumentChunk.project_id == project_id)
    )
    if concept_id is not None:
        scope = scope.filter(DocumentChunk.concept_id == concept_id)
    if scope.limit(1).first() is None:
        return []

    query_vector = embedding_client.embed_one(query.strip())
    if len(query_vector) != EMBEDDING_DIMS:
        raise ValueError(
            f"query embedding has {len(query_vector)} dims, expected {EMBEDDING_DIMS}."
        )

    distance = Embedding.embedding.cosine_distance(query_vector)
    q = (
        db.query(DocumentChunk, distance.label("score"))
        .join(Embedding, Embedding.chunk_id == DocumentChunk.id)
        .filter(Embedding.project_id == project_id, DocumentChunk.project_id == project_id)
    )
    if concept_id is not None:
        q = q.filter(DocumentChunk.concept_id == concept_id)
    rows = q.order_by(distance).limit(top_k).all()

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            material_id=chunk.material_id,
            content=chunk.content,
            page_number=chunk.page_number,
            source_name=chunk.source_name,
            chunk_index=chunk.chunk_index,
            score=float(score),
        )
        for chunk, score in rows
    ]
