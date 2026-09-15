"""Deterministic text chunking for retrieval — Phase 27.

Splits source text into retrieval-sized windows (~500 tokens / ~2000 chars,
~50 tokens / ~200 chars overlap per blueprint §RAG). Pure application logic:
no LLM chooses boundaries. Chunking is repeatable — the same source text
always produces the same chunks.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.material import Material
from app.models.project import Project

# Retrieval-sized boundaries (~4 chars/token): 500 tokens / 50 tokens overlap.
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200


def _validate_params(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


def _back_off_to_word(text: str, start: int, end: int) -> int:
    """Move end back to a word boundary (whitespace) unless no space in window."""
    i = end - 1
    while i > start and not text[i].isspace():
        i -= 1
    if i == start:
        # No whitespace in window (super-long token) — hard cut.
        return end
    return i  # end lands on whitespace; stripped span ends at a word end


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[dict]:
    """Split text into overlapping chunks.

    Returns [{text, start_offset, end_offset}] with the invariant
    ``text == source[start_offset:end_offset]`` for every chunk.
    Consecutive chunks overlap (``start[i+1] < end[i]``) unless
    ``overlap=0``. Raises ValueError on empty input or bad params.
    """
    if not text or not text.strip():
        raise ValueError("text must be a non-empty string")
    _validate_params(chunk_size, overlap)

    n = len(text)
    drafts: list[dict] = []
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            end = _back_off_to_word(text, start, end)
            if end <= start:
                end = min(start + chunk_size, n)
        # Strip padding whitespace; keep offsets exact for the stripped span.
        s, e = start, end
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            drafts.append({"text": text[s:e], "start_offset": s, "end_offset": e})
        if end >= n:
            break
        next_start = end - overlap
        # Snap forward to a word start so chunks never begin mid-word.
        # Falls back to the raw offset when the overlap holds no word
        # start (super-long token) — a hard cut is unavoidable there.
        j = next_start
        while j < end and not text[j].isspace():
            j += 1
        k = j
        while k < end and text[k].isspace():
            k += 1
        if k < end:
            next_start = k
        start = next_start if next_start > start else start + 1
    if not drafts:
        raise ValueError("text contains no chunkable content")
    return drafts


def chunk_pages(
    pages: list[str],
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[dict]:
    """Chunk per-page texts without ever spanning a page boundary.

    Empty pages yield no chunks. Each draft carries 1-indexed page_number.
    """
    _validate_params(chunk_size, overlap)
    drafts: list[dict] = []
    for i, page_text in enumerate(pages):
        if not page_text or not page_text.strip():
            continue
        for d in chunk_text(page_text, chunk_size=chunk_size, overlap=overlap):
            drafts.append({**d, "page_number": i + 1})
    return drafts


def persist_chunks(
    db: Session,
    project_id: uuid.UUID,
    material_id: uuid.UUID,
    drafts: list[dict],
    source_name: str | None = None,
) -> dict[str, int]:
    """Replace a material's chunks with new drafts (blueprint idempotency).

    Deletes existing chunks for material_id before insert, so a retried run
    never duplicates chunks. Single commit; rollback on error.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    material = db.get(Material, material_id)
    if not material or material.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    try:
        db.query(DocumentChunk).filter(DocumentChunk.material_id == material_id).delete(
            synchronize_session=False
        )
        for idx, d in enumerate(drafts):
            db.add(
                DocumentChunk(
                    project_id=project_id,
                    material_id=material_id,
                    concept_id=d.get("concept_id"),
                    topic_id=d.get("topic_id"),
                    subtopic_id=d.get("subtopic_id"),
                    page_number=d.get("page_number"),
                    source_name=source_name,
                    chunk_index=idx,
                    content=d["text"],
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"chunks": db.query(DocumentChunk).filter(DocumentChunk.material_id == material_id).count()}
