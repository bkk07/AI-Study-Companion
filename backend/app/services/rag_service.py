"""Consumer-neutral RAG foundation — retrieval + bounded context (Phase 31).

Shared by tutor, quiz, and assessment consumers: takes a query plus scope,
retrieves ranked chunks, and assembles a char-bounded context payload that
keeps citation metadata on every item. No LLM call here, no endpoint, and no
consumer-specific wording — downstream services decide what "no context"
means (e.g. tutor's unsupported-question behavior).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.schemas.rag import RagChunk, RagContext
from app.services import retrieval_service

DEFAULT_MAX_CHUNKS = 5
MAX_MAX_CHUNKS = 10
DEFAULT_MAX_CHARS = 6000
MIN_MAX_CHARS = 500
MAX_MAX_CHARS = 20000
_TRUNCATION_MARKER = "…"


def _snap_truncate(text: str, limit: int) -> str:
    """Shorten to limit chars, snapping back to a word end; raw cut fallback."""
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - len(_TRUNCATION_MARKER))].rstrip()
    snapped = cut.rsplit(None, 1)[0] if cut.strip() else ""
    return (snapped or text[: max(0, limit - len(_TRUNCATION_MARKER))].rstrip()) + _TRUNCATION_MARKER


def assemble_context(
    db: Session,
    *,
    project_id: uuid.UUID,
    query: str,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    max_chars: int = DEFAULT_MAX_CHARS,
    concept_id: uuid.UUID | None = None,
) -> RagContext:
    """Retrieve scoped chunks and assemble a bounded, citable context."""
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    max_chunks = max(1, min(int(max_chunks), MAX_MAX_CHUNKS))
    max_chars = max(MIN_MAX_CHARS, min(int(max_chars), MAX_MAX_CHARS))

    hits = retrieval_service.retrieve(
        db,
        project_id=project_id,
        query=query.strip(),
        top_k=max_chunks,
        concept_id=concept_id,
    )

    usable = [h for h in hits if (h.content or "").strip()]
    chunks: list[RagChunk] = []
    total_chars = 0
    processed = 0
    char_cut = False
    for hit in usable:
        if len(chunks) >= max_chunks or total_chars >= max_chars:
            break
        content = hit.content.strip()
        room = max_chars - total_chars
        if len(content) > room:
            content = _snap_truncate(content, room)
            char_cut = True
        chunks.append(
            RagChunk(
                chunk_id=hit.chunk_id,
                material_id=hit.material_id,
                content=content,
                page_number=hit.page_number,
                source_name=hit.source_name,
                chunk_index=hit.chunk_index,
                score=hit.score,
            )
        )
        total_chars += len(content)
        processed += 1
    truncated = char_cut or processed < len(usable)

    return RagContext(
        query=query.strip(),
        scope_project_id=project_id,
        scope_concept_id=concept_id,
        chunks=chunks,
        total_chars=total_chars,
        truncated=truncated,
    )
