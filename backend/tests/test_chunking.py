import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.services.chunking_service import (
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    chunk_pages,
    chunk_text,
    persist_chunks,
)

WORD = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "


def _long_text(chars: int) -> str:
    reps = chars // len(WORD) + 2
    return (WORD * reps)[:chars].rstrip()


# ------------------------------------------------------------- boundaries ---


def test_short_text_single_chunk_exact_span():
    text = "Hello study world 123"
    drafts = chunk_text(text)
    assert len(drafts) == 1
    assert drafts[0]["text"] == text
    assert (drafts[0]["start_offset"], drafts[0]["end_offset"]) == (0, len(text))


def test_exact_size_text_single_chunk():
    text = _long_text(CHUNK_SIZE_CHARS)
    assert len(text) == CHUNK_SIZE_CHARS
    drafts = chunk_text(text)
    assert len(drafts) == 1
    assert drafts[0]["end_offset"] - drafts[0]["start_offset"] <= CHUNK_SIZE_CHARS


def test_long_text_sizes_overlap_and_coverage():
    text = _long_text(5500)
    drafts = chunk_text(text)
    assert len(drafts) >= 3
    for d in drafts:
        assert len(d["text"]) <= CHUNK_SIZE_CHARS
        assert d["text"] == text[d["start_offset"] : d["end_offset"]]  # offset invariant
    assert drafts[0]["start_offset"] == 0
    assert drafts[-1]["end_offset"] == len(text)
    for prev, nxt in zip(drafts, drafts[1:]):
        assert nxt["start_offset"] < prev["end_offset"]  # overlap exists
        assert nxt["start_offset"] > prev["start_offset"]  # progress
        shared = text[nxt["start_offset"] : prev["end_offset"]]
        assert shared and shared in prev["text"] and shared in nxt["text"]
    # full coverage: gaps between spans are whitespace-only
    for prev, nxt in zip(drafts, drafts[1:]):
        assert text[prev["end_offset"] : nxt["start_offset"]].strip() == ""


def test_cuts_fall_on_word_boundaries():
    text = _long_text(5000)
    drafts = chunk_text(text)
    assert len(drafts) > 1
    for d in drafts[1:]:
        s = d["start_offset"]
        assert s == 0 or text[s - 1].isspace(), f"mid-word start at {s}: {text[s-5:s+5]!r}"
    for d in drafts[:-1]:
        e = d["end_offset"]
        assert e == len(text) or text[e].isspace(), f"mid-word end at {e}: {text[e-5:e+5]!r}"


def test_super_long_token_hard_cut():
    text = "x" * 3000
    drafts = chunk_text(text)
    assert [len(d["text"]) for d in drafts] == [CHUNK_SIZE_CHARS, 3000 - (CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS)]
    assert drafts[1]["start_offset"] == CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS


def test_zero_overlap_contiguous_up_to_whitespace():
    text = _long_text(4500)
    drafts = chunk_text(text, overlap=0)
    assert len(drafts) > 1
    for prev, nxt in zip(drafts, drafts[1:]):
        # separator whitespace belongs to neither stripped span
        assert text[prev["end_offset"] : nxt["start_offset"]].strip() == ""
        assert nxt["start_offset"] >= prev["end_offset"]


def test_custom_small_window():
    text = "aa bb cc dd ee ff gg hh ii jj kk ll mm nn oo pp"
    drafts = chunk_text(text, chunk_size=10, overlap=3)
    assert len(drafts) > 2
    joined = " ".join(d["text"] for d in drafts)
    for word in ["aa", "jj", "pp"]:
        assert word in joined


def test_empty_and_bad_params_raise():
    with pytest.raises(ValueError):
        chunk_text("")
    with pytest.raises(ValueError):
        chunk_text("   \n  ")
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("hello", overlap=-1)
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=100, overlap=100)
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=100, overlap=150)


def test_deterministic_repeatable():
    text = _long_text(4200)
    assert chunk_text(text) == chunk_text(text)


# ------------------------------------------------------------------ pages ---


def test_chunk_pages_never_spans_boundary():
    pages = ["first page alpha beta gamma", "", "third page delta epsilon"]
    drafts = chunk_pages(pages)
    assert [d["page_number"] for d in drafts] == [1, 3]  # empty page skipped
    assert "alpha" in drafts[0]["text"]
    assert "delta" in drafts[1]["text"]
    # no draft mixes pages
    assert "alpha" not in drafts[1]["text"] and "delta" not in drafts[0]["text"]


def test_chunk_pages_long_page_splits_within_page():
    pages = [_long_text(4500), "short two"]
    drafts = chunk_pages(pages)
    p1 = [d for d in drafts if d["page_number"] == 1]
    p2 = [d for d in drafts if d["page_number"] == 2]
    assert len(p1) > 1 and len(p2) == 1
    for d in p1:
        assert d["text"] in pages[0]


# ---------------------------------------------------------------- persist ---


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _client_and_engine():
    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def test_persist_replace_stable_and_isolated():
    from unittest.mock import MagicMock, patch

    from app.models.chunk import DocumentChunk

    client, engine = _client_and_engine()
    try:
        email = f"ch_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        token = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        space = client.post("/api/v1/spaces", json={"name": "S"}, headers=h).json()["id"]
        proj = client.post(f"/api/v1/spaces/{space}/projects", json={"name": "P"}, headers=h).json()["id"]

        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.material import Material

        mat = Material(project_id=uuid.UUID(proj), filename="a.pdf", storage_path="/tmp/a.pdf", status="ready")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        mid = mat.id
        db.close()

        text = _long_text(4500)
        drafts = chunk_text(text)
        db = Sess()
        out1 = persist_chunks(db, uuid.UUID(proj), mid, drafts, source_name="a.pdf")
        assert out1 == {"chunks": len(drafts)}
        rows1 = db.query(DocumentChunk).filter(DocumentChunk.material_id == mid).order_by(DocumentChunk.chunk_index).all()
        assert [r.chunk_index for r in rows1] == list(range(len(drafts)))
        assert all(r.project_id == uuid.UUID(proj) and r.source_name == "a.pdf" for r in rows1)
        assert "".join(r.content for r in rows1) != ""  # sanity
        contents1 = [r.content for r in rows1]
        db.close()

        # re-persist identical: count + contents stable, no duplicates
        db = Sess()
        out2 = persist_chunks(db, uuid.UUID(proj), mid, drafts, source_name="a.pdf")
        assert out2 == out1
        rows2 = db.query(DocumentChunk).filter(DocumentChunk.material_id == mid).all()
        assert sorted(r.content for r in rows2) == sorted(contents1)
        db.close()

        # second material isolated
        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_task.delay.return_value = MagicMock(id="m")
            pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
            mid2 = client.post(
                f"/api/v1/projects/{proj}/materials",
                files={"file": ("b.pdf", pdf, "application/pdf")},
                headers=h,
            ).json()["id"]
        db = Sess()
        persist_chunks(db, uuid.UUID(proj), uuid.UUID(mid2), chunk_text("tiny doc"), source_name="b.pdf")
        assert db.query(DocumentChunk).filter(DocumentChunk.material_id == mid).count() == len(drafts)
        assert db.query(DocumentChunk).filter(DocumentChunk.material_id == uuid.UUID(mid2)).count() == 1
        db.close()

        # missing material -> 404, nothing written
        db = Sess()
        with pytest.raises(Exception, match="Material not found"):
            persist_chunks(db, uuid.UUID(proj), uuid.uuid4(), drafts)
        db.close()

        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)
