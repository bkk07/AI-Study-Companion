"""Phase 31 — context assembly unit tests with mocked retrieval (no DB)."""

import uuid
from unittest.mock import patch

import pytest

from app.services import rag_service
from app.services.retrieval_service import RetrievedChunk

PID = uuid.uuid4()
CID = uuid.uuid4()
MID = uuid.uuid4()


def _hit(text: str, score: float = 0.1, **kw) -> RetrievedChunk:
    base = dict(
        chunk_id=uuid.uuid4(),
        material_id=MID,
        content=text,
        page_number=2,
        source_name="doc.pdf",
        chunk_index=3,
        score=score,
    )
    base.update(kw)
    return RetrievedChunk(**base)


def test_scope_passthrough_and_metadata_preserved():
    hits = [_hit("alpha beta gamma", 0.05), _hit("delta epsilon", 0.2)]
    with patch("app.services.rag_service.retrieval_service") as mc:
        mc.retrieve.return_value = hits
        ctx = rag_service.assemble_context(
            None, project_id=PID, query="  what is alpha?  ", max_chunks=5, concept_id=CID
        )
    mc.retrieve.assert_called_once_with(
        None, project_id=PID, query="what is alpha?", top_k=5, concept_id=CID
    )
    assert ctx.query == "what is alpha?"
    assert ctx.scope_project_id == PID
    assert ctx.scope_concept_id == CID
    assert [c.content for c in ctx.chunks] == ["alpha beta gamma", "delta epsilon"]
    assert ctx.chunks[0].chunk_id == hits[0].chunk_id
    assert ctx.chunks[0].material_id == MID
    assert (ctx.chunks[0].page_number, ctx.chunks[0].source_name, ctx.chunks[0].chunk_index) == (2, "doc.pdf", 3)
    assert ctx.chunks[0].score == 0.05
    assert ctx.total_chars == len("alpha beta gamma") + len("delta epsilon")
    assert ctx.truncated is False


def test_char_bound_word_snapped_with_marker():
    text = "word " * 200  # 1000 chars
    with patch("app.services.rag_service.retrieval_service") as mc:
        mc.retrieve.return_value = [_hit(text)]
        ctx = rag_service.assemble_context(None, project_id=PID, query="q", max_chars=500)
    assert ctx.total_chars <= 500
    assert ctx.truncated is True
    body = ctx.chunks[0].content
    assert body.endswith("…")
    assert not body[:-1].endswith(" ")  # snapped, no dangling space before marker
    assert " ".join(body[:-1].split()) == body[:-1].strip()


def test_count_bound_drops_rest_and_marks_truncated():
    hits = [_hit(f"chunk number {i} text", score=0.1 * i) for i in range(5)]
    with patch("app.services.rag_service.retrieval_service") as mc:
        mc.retrieve.return_value = hits
        ctx = rag_service.assemble_context(None, project_id=PID, query="q", max_chunks=2)
    mc.retrieve.assert_called_once_with(None, project_id=PID, query="q", top_k=2, concept_id=None)
    assert [c.content for c in ctx.chunks] == ["chunk number 0 text", "chunk number 1 text"]
    assert ctx.truncated is True


def test_empty_retrieval_gives_empty_untruncated_context():
    with patch("app.services.rag_service.retrieval_service") as mc:
        mc.retrieve.return_value = []
        ctx = rag_service.assemble_context(None, project_id=PID, query="obscure query")
    assert ctx.chunks == []
    assert ctx.total_chars == 0
    assert ctx.truncated is False


def test_empty_contents_skipped_without_truncation():
    hits = [_hit("   "), _hit("real content here")]
    with patch("app.services.rag_service.retrieval_service") as mc:
        mc.retrieve.return_value = hits
        ctx = rag_service.assemble_context(None, project_id=PID, query="q")
    assert [c.content for c in ctx.chunks] == ["real content here"]
    assert ctx.truncated is False


def test_empty_query_raises_without_retrieval_call():
    with patch("app.services.rag_service.retrieval_service") as mc:
        with pytest.raises(ValueError):
            rag_service.assemble_context(None, project_id=PID, query="   ")
        mc.retrieve.assert_not_called()
