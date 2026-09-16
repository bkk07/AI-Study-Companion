"""Hybrid PDF routing tests — per-page PyMuPDF TEXT vs Tesseract OCR.

Tesseract itself is never invoked here (no binary on test hosts): OCR is
mocked at `ocr_service.ocr_fitz_page`, which is the single seam the router
uses. Image-only pages are real PyMuPDF image XObjects, so routing
decisions (text? images? → OCR?) are genuinely exercised.
"""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.services import job_service
from app.services.document_extraction_service import (
    extract_document_pages,
    extract_pdf_text,
    is_meaningful_text,
)
from app.services.ocr_service import OcrError

OCR_SEAM = "app.services.ocr_service.ocr_fitz_page"

OCR_TEXT = "Scanned invoice for acme supplies totalling forty two dollars paid in full"


def _text_pdf(path: str, texts: list[str]) -> None:
    doc = fitz.open()
    for t in texts:
        page = doc.new_page()
        page.insert_text((72, 72), t)
    doc.save(path)
    doc.close()


def _image_page(page: "fitz.Page", text: str | None = None) -> None:
    """Embed a real image XObject (scanned-page stand-in), optional text too."""
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200))
    pix.clear_with(200)
    page.insert_image(fitz.Rect(72, 72, 272, 272), pixmap=pix)
    if text:
        page.insert_text((72, 300), text)


def _mixed_pdf(path: str) -> None:
    """Page 1 TEXT, page 2 scanned, page 3 TEXT, page 4 scanned."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "First chapter introduces the water cycle in full detail here")
    _image_page(doc.new_page())
    p3 = doc.new_page()
    p3.insert_text((72, 72), "Third chapter covers evaporation and condensation stages fully")
    _image_page(doc.new_page())
    doc.save(path)
    doc.close()


# ------------------------------------------------------- threshold unit ----


def test_meaningful_threshold():
    assert not is_meaningful_text("")
    assert not is_meaningful_text("   \n  ")
    assert not is_meaningful_text(None)
    assert not is_meaningful_text("Page 3")  # folio fragment — not body content
    assert is_meaningful_text("The quick brown fox jumps over the lazy dog today")
    assert is_meaningful_text(OCR_TEXT)


# ------------------------------------------------------------- Test 1 ------


def test_normal_pdf_routes_all_text_no_ocr():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "normal.pdf")
    _text_pdf(p, ["Normal selectable text about photosynthesis in green plants", "Second page on cellular respiration processes at length"])
    with patch(OCR_SEAM) as mock_ocr:
        pages = extract_document_pages(p)
        text, count = extract_pdf_text(p)
    assert count == 2
    assert [pg["extraction_method"] for pg in pages] == ["TEXT", "TEXT"]
    assert all(pg["ocr_error"] is None for pg in pages)
    mock_ocr.assert_not_called()
    assert "photosynthesis" in text


# ------------------------------------------------------------- Test 2 ------


def test_scanned_pdf_routes_ocr_and_succeeds():
    """Previously: ValueError 'no extractable text' → FAILED. Now: READY path."""
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "scanned.pdf")
    doc = fitz.open()
    _image_page(doc.new_page())
    doc.save(p)
    doc.close()
    with patch(OCR_SEAM, return_value=OCR_TEXT) as mock_ocr:
        pages = extract_document_pages(p)
    assert mock_ocr.call_count == 1
    assert pages[0]["extraction_method"] == "OCR"
    assert pages[0]["has_images"] is True
    assert pages[0]["page_number"] == 1
    with patch(OCR_SEAM, return_value=OCR_TEXT):
        text, count = extract_pdf_text(p)
    assert "forty two dollars" in text
    assert count == 1


# ------------------------------------------------------------- Test 3 ------


def test_mixed_pdf_routes_each_page_independently():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "mixed.pdf")
    _mixed_pdf(p)
    with patch(OCR_SEAM, return_value=OCR_TEXT) as mock_ocr:
        pages = extract_document_pages(p)
    assert [pg["extraction_method"] for pg in pages] == ["TEXT", "OCR", "TEXT", "OCR"]
    assert mock_ocr.call_count == 2  # only scanned pages invoke Tesseract
    with patch(OCR_SEAM, return_value=OCR_TEXT):
        text, count = extract_pdf_text(p)
    assert "water cycle" in text and "forty two dollars" in text
    assert count == 4


# ------------------------------------------------------------- Test 4 ------


def test_text_plus_diagram_stays_text_no_ocr():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "diagram.pdf")
    doc = fitz.open()
    page = doc.new_page()
    _image_page(page, "Mitochondria produce cellular energy through respiration daily")
    doc.save(p)
    doc.close()
    with patch(OCR_SEAM) as mock_ocr:
        pages = extract_document_pages(p)
    assert pages[0]["extraction_method"] == "TEXT"
    assert pages[0]["has_images"] is True  # image reference preserved for future vision
    mock_ocr.assert_not_called()


# ------------------------------------------------------------- Test 5 ------


def test_empty_pages_skipped_without_crashing():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "gap.pdf")
    doc = fitz.open()
    pg1 = doc.new_page()
    pg1.insert_text((72, 72), "Opening chapter with plenty of meaningful study content")
    doc.new_page()  # truly blank: no text, no images
    pg3 = doc.new_page()
    pg3.insert_text((72, 72), "Closing chapter with plenty of meaningful study content")
    doc.save(p)
    doc.close()
    with patch(OCR_SEAM) as mock_ocr:
        pages = extract_document_pages(p)
        text, count = extract_pdf_text(p)
    assert [pg["extraction_method"] for pg in pages] == ["TEXT", "EMPTY", "TEXT"]
    mock_ocr.assert_not_called()  # nothing to OCR on a blank page
    assert "Opening chapter" in text and "Closing chapter" in text
    assert count == 3


def test_all_empty_document_still_fails_diagnosably():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "blank.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.save(p)
    doc.close()
    with pytest.raises(ValueError, match="no extractable text"):
        extract_pdf_text(p)


# ------------------------------------------------------------- Test 6 ------


def test_ocr_failure_degrades_page_not_document():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "ocrfail.pdf")
    doc = fitz.open()
    pg1 = doc.new_page()
    pg1.insert_text((72, 72), "Reliable chapter content that extracts cleanly every time")
    _image_page(doc.new_page())
    doc.save(p)
    doc.close()
    with patch(OCR_SEAM, side_effect=OcrError("tesseract missing")):
        pages = extract_document_pages(p)
        text, _ = extract_pdf_text(p)  # other pages carry the document to READY
    assert pages[1]["extraction_method"] == "EMPTY"
    assert "tesseract missing" in (pages[1]["ocr_error"] or "")
    assert "Reliable chapter" in text


def test_total_ocr_failure_fails_with_ocr_hint():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "allfail.pdf")
    doc = fitz.open()
    _image_page(doc.new_page())
    doc.save(p)
    doc.close()
    with patch(OCR_SEAM, side_effect=OcrError("tesseract missing")), pytest.raises(ValueError, match="OCR failed"):
        extract_pdf_text(p)


def test_ocr_disabled_routes_scans_to_empty():
    d = tempfile.mkdtemp(prefix="hy_")
    p = os.path.join(d, "disabled.pdf")
    doc = fitz.open()
    _image_page(doc.new_page())
    pg2 = doc.new_page()
    pg2.insert_text((72, 72), "Normal chapter text with sufficient length for routing")
    doc.save(p)
    doc.close()
    with patch(OCR_SEAM) as mock_ocr:
        pages = extract_document_pages(p, ocr_enabled=False)
        text, _ = extract_pdf_text(p, ocr_enabled=False)
    mock_ocr.assert_not_called()
    assert pages[0]["extraction_method"] == "EMPTY"
    assert "disabled" in (pages[0]["ocr_error"] or "")
    assert "Normal chapter" in text


# ------------------------------------------- chunk method + pipeline ------


def test_chunk_pages_carries_extraction_method():
    from app.services.chunking_service import chunk_pages

    drafts = chunk_pages(
        ["Photosynthesis converts sunlight into chemical energy stores", ""],
        methods=["OCR", "EMPTY"],
    )
    assert len(drafts) == 1
    assert drafts[0]["page_number"] == 1
    assert drafts[0]["extraction_method"] == "OCR"

    legacy = chunk_pages(["Plain text page with enough words for chunking here"])
    assert legacy[0]["extraction_method"] == "TEXT"


# ------------------------------------------------------------- Test 7 ------
# Traceability: OCR chunks keep document/page/method and stay retrievable.


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _override_and_client(tmpdir: str | None = None):
    os.environ["DATABASE_URL"] = _host_url()
    if tmpdir:
        os.environ["UPLOAD_DIR"] = tmpdir
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


def _teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()
    os.environ.pop("UPLOAD_DIR", None)


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _cleanup(email: str, engine):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()


def test_scanned_pipeline_end_to_end_traceability_and_retrieval():
    """Mixed PDF → process_pdf (mocked OCR) → READY, ocr_pages counted,
    chunks carry page_number + extraction_method, OCR chunk retrievable."""
    from app.models.chunk import DocumentChunk
    from app.models.embedding import EMBEDDING_DIMS, Embedding
    from app.models.material import Material
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"hy_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
            sid = resp.json()["id"]
            resp = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers)
            proj_id = resp.json()["id"]

        pdf_path = os.path.join(tmpdir, proj_id, "hybrid.pdf")
        Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        pg1 = doc.new_page()
        pg1.insert_text((72, 72), "River systems shape valleys through erosion over long ages")
        _image_page(doc.new_page())
        doc.save(pdf_path)
        doc.close()

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = Material(project_id=uuid.UUID(proj_id), filename="hybrid.pdf", storage_path=pdf_path, status="pending")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
        mid, jid = str(mat.id), str(job.id)
        db.close()

        with patch(OCR_SEAM, return_value=OCR_TEXT):
            result = process_pdf.apply(args=[jid, mid]).get()
        assert result["status"] == "completed"
        assert result["ocr_pages"] == 1
        assert result["chunks"] == 2

        db2 = Sess()
        mat2 = db2.get(Material, uuid.UUID(mid))
        assert mat2.status == "ready"
        rows = (
            db2.query(DocumentChunk)
            .filter(DocumentChunk.material_id == uuid.UUID(mid))
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        by_method = {r.extraction_method: r for r in rows}
        assert set(by_method) == {"TEXT", "OCR"}
        assert by_method["TEXT"].page_number == 1
        assert by_method["OCR"].page_number == 2
        assert "forty two dollars" in by_method["OCR"].content

        # RAG retrieval over local one-hot vectors returns the OCR chunk.
        one_hot = [1.0] + [0.0] * (EMBEDDING_DIMS - 1)
        for r in rows:
            db2.add(Embedding(project_id=uuid.UUID(proj_id), material_id=uuid.UUID(mid), chunk_id=r.id, embedding=one_hot))
        db2.commit()
        from app.services import retrieval_service

        with patch.object(retrieval_service.embedding_client, "embed_one", return_value=list(one_hot)):
            hits = retrieval_service.retrieve(db2, project_id=uuid.UUID(proj_id), query="invoice dollars")
        assert any(h.page_number == 2 and "forty two dollars" in h.content for h in hits)
        db2.close()
        _cleanup(email, engine)
    finally:
        _teardown(engine)
