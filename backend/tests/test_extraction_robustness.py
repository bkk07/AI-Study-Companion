"""Robustness suite for PDF extraction — the most critical pipeline phase.

Covers service / worker-task / upload layers across document varieties:
single + multi-page, empty, whitespace-only, corrupt, truncated, non-PDF
bytes, missing paths, directories, large docs, unicode (when a capable font
exists), and multi-line pages. PDFs are generated in tmpdirs (never committed).
"""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.services import job_service
from app.services.document_extraction_service import extract_pages, extract_pdf_text

# ---------------------------------------------------------------- helpers ---


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


def _make_pdf(path: str, texts: list[str], fontfile: str | None = None, fontname: str = "tfont"):
    doc = fitz.open()
    for t in texts:
        page = doc.new_page()
        if fontfile:
            try:
                page.insert_font(fontname=fontname, fontfile=fontfile)
            except Exception:
                pass  # already registered in this doc
            page.insert_text((72, 72), t, fontname=fontname)
        else:
            page.insert_text((72, 72), t)
    doc.save(path)
    doc.close()


def _pdf_bytes(texts: list[str]) -> bytes:
    doc = fitz.open()
    for t in texts:
        page = doc.new_page()
        page.insert_text((72, 72), t)
    data = doc.tobytes()
    doc.close()
    return bytes(data)


def _find_font(candidates: list[str]) -> str | None:
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


UNICODE_FONT = _find_font(
    [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
)
CJK_FONT = _find_font(
    [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
)

# ------------------------------------------------------------- service ------


def test_service_single_page_basic():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "one.pdf")
    _make_pdf(p, ["The quick brown fox jumps over 12345!"])
    text, count = extract_pdf_text(p)
    assert count == 1
    assert isinstance(text, str)
    assert "quick brown fox" in text
    assert "12345" in text


def test_service_five_pages_order_and_numbers():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "five.pdf")
    wants = [f"Chapter {i} content marker-{i}" for i in range(1, 6)]
    _make_pdf(p, wants)
    text, count = extract_pdf_text(p)
    assert count == 5
    # order preserved in joined text
    positions = [text.index(f"marker-{i}") for i in range(1, 6)]
    assert positions == sorted(positions)
    pages = extract_pages(p)
    assert len(pages) == 5
    assert [pg["page_number"] for pg in pages] == [1, 2, 3, 4, 5]
    for pg, want in zip(pages, wants):
        assert want in pg["text"]


def test_service_middle_empty_page_slot_kept():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "gap.pdf")
    doc = fitz.open()
    for t in ["first page words", None, "third page words"]:
        page = doc.new_page()
        if t:
            page.insert_text((72, 72), t)
    doc.save(p)
    doc.close()
    text, count = extract_pdf_text(p)
    assert count == 3
    assert "first page words" in text
    assert "third page words" in text
    pages = extract_pages(p)
    assert len(pages) == 3
    assert pages[1]["page_number"] == 2
    assert pages[1]["text"] == ""


def test_service_blank_pdf_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "blank.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.save(p)
    doc.close()
    with pytest.raises(ValueError, match="no extractable text"):
        extract_pdf_text(p)


def test_service_whitespace_only_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "ws.pdf")
    _make_pdf(p, ["   "])
    with pytest.raises(ValueError):
        extract_pdf_text(p)


def test_service_corrupt_bytes_raise():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "corrupt.pdf")
    Path(p).write_bytes(b"not a pdf at all, just text")
    with pytest.raises(ValueError):
        extract_pdf_text(p)


def test_service_truncated_header_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "trunc.pdf")
    Path(p).write_bytes(b"%PDF-1.4\n%garbage truncated body without objects")
    with pytest.raises(ValueError):
        extract_pdf_text(p)


def test_service_plain_text_with_pdf_suffix_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "fake.pdf")
    Path(p).write_bytes(b"hello plain text, no pdf magic here")
    with pytest.raises(ValueError):
        extract_pdf_text(p)


def test_service_empty_file_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "empty.pdf")
    Path(p).write_bytes(b"")
    with pytest.raises(ValueError):
        extract_pdf_text(p)


def test_service_missing_file_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    with pytest.raises(FileNotFoundError):
        extract_pdf_text(os.path.join(d, "nope.pdf"))


def test_service_directory_path_raises():
    d = tempfile.mkdtemp(prefix="xr_")
    with pytest.raises(ValueError):
        extract_pdf_text(d)


def test_service_large_twenty_pages():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "big.pdf")
    _make_pdf(p, [f"bulk content page {i} lorem ipsum dolor" for i in range(1, 21)])
    text, count = extract_pdf_text(p)
    assert count == 20
    assert "bulk content page 1" in text
    assert "bulk content page 20" in text
    assert len(extract_pages(p)) == 20


def test_service_multiline_same_page():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "multi.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "alpha line one")
    page.insert_text((72, 92), "beta line two")
    page.insert_text((72, 112), "gamma 999")
    doc.save(p)
    doc.close()
    text, count = extract_pdf_text(p)
    assert count == 1
    assert "alpha line one" in text
    assert "beta line two" in text
    assert "gamma 999" in text


def test_service_special_ascii_roundtrip():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "ascii.pdf")
    sample = "Numbers 0123456789; symbols !@#$%^&*()_+-=[]{}|;:,.<>?/ mixed CASE Words"
    _make_pdf(p, [sample])
    text, _ = extract_pdf_text(p)
    assert "0123456789" in text
    assert "mixed CASE Words" in text


@pytest.mark.skipif(UNICODE_FONT is None, reason="no unicode TTF available on this host")
def test_service_unicode_accents_euro_greek():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "uni.pdf")
    _make_pdf(p, ["caf\u00e9 na\u00efve \u00fcber \u20ac92 \u03b1\u03b2\u03b3"], fontfile=UNICODE_FONT)
    text, count = extract_pdf_text(p)
    assert count == 1
    assert "caf\u00e9" in text
    assert "\u20ac" in text
    assert "\u03b1\u03b2" in text


@pytest.mark.skipif(CJK_FONT is None, reason="no CJK font available on this host")
def test_service_cjk_roundtrip():
    d = tempfile.mkdtemp(prefix="xr_")
    p = os.path.join(d, "cjk.pdf")
    _make_pdf(p, ["\u4e2d\u6587\u6d4b\u8bd5\u5185\u5bb9"], fontfile=CJK_FONT, fontname="cjkf")
    text, count = extract_pdf_text(p)
    assert count == 1
    assert "\u4e2d\u6587\u6d4b\u8bd5" in text


# ---------------------------------------------------------------- task ------


def _setup_space_project(client: TestClient, headers: dict) -> str:
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
    sid = resp.json()["id"]
    resp = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers)
    return resp.json()["id"]


def test_task_multipage_persists_all_text():
    from app.models.material import Material
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xrm_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _setup_space_project(client, headers)

        pdf_path = os.path.join(tmpdir, proj_id, "multi.pdf")
        Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
        _make_pdf(pdf_path, ["task page one apple", "task page two banana", "task page three cherry"])

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = Material(project_id=uuid.UUID(proj_id), filename="multi.pdf", storage_path=pdf_path, status="pending")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
        mid, jid = str(mat.id), str(job.id)
        db.close()

        result = process_pdf.apply(args=[jid, mid]).get()
        assert result["status"] == "completed"
        assert result["page_count"] == 3

        db2 = Sess()
        mat2 = db2.get(Material, uuid.UUID(mid))
        assert mat2.status == "ready"
        assert mat2.page_count == 3
        assert "apple" in mat2.extracted_text
        assert "banana" in mat2.extracted_text
        assert "cherry" in mat2.extracted_text
        assert job_service.get_job(db2, uuid.UUID(jid)).status == "completed"
        db2.close()
        _cleanup(email, engine)
    finally:
        _teardown(engine)


def test_task_blank_pdf_fails_diagnosably():
    from app.models.material import Material
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xrb_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _setup_space_project(client, headers)

        bad_path = os.path.join(tmpdir, "blank.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(bad_path)
        doc.close()

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = Material(project_id=uuid.UUID(proj_id), filename="blank.pdf", storage_path=bad_path, status="pending")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
        mid, jid = str(mat.id), str(job.id)
        db.close()

        result = process_pdf.apply(args=[jid, mid]).get()
        assert result["status"] == "failed"
        db2 = Sess()
        mat2 = db2.get(Material, uuid.UUID(mid))
        assert mat2.status == "failed"
        assert mat2.extracted_text is None
        assert mat2.error_message
        assert job_service.get_job(db2, uuid.UUID(jid)).status == "failed"
        db2.close()
        _cleanup(email, engine)
    finally:
        _teardown(engine)


def test_task_valid_job_missing_material_marks_job_failed_then_raises():
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xrn_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _setup_space_project(client, headers)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.material import Material

        mat = Material(
            project_id=uuid.UUID(proj_id),
            filename="ghost.pdf",
            storage_path=os.path.join(tmpdir, "ghost.pdf"),
            status="pending",
        )
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
        jid = str(job.id)
        ghost_mid = str(uuid.uuid4())  # material that does not exist
        db.close()

        with pytest.raises(ValueError, match="not found"):
            process_pdf.apply(args=[jid, ghost_mid]).get()

        db2 = Sess()
        assert job_service.get_job(db2, uuid.UUID(jid)).status == "failed"
        db2.close()
        _cleanup(email, engine)
    finally:
        _teardown(engine)


def test_task_malformed_ids_raise_without_db_touch():
    from app.worker.tasks.extraction import process_pdf

    with pytest.raises(ValueError, match="Invalid job/material id"):
        process_pdf.apply(args=["not-a-uuid", "also-bad"]).get()


# --------------------------------------------------------------- upload -----


def test_upload_multipage_pdf_end_to_end_bytes():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xru_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_task.delay.return_value = MagicMock(id="celery-x")
            proj_id = _setup_space_project(client, headers)
            data = _pdf_bytes(["upload page one", "upload page two"])
            resp = client.post(
                f"/api/v1/projects/{proj_id}/materials",
                files={"file": ("multi.pdf", data, "application/pdf")},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            body = resp.json()
            assert body["status"] == "pending"
            assert os.path.exists(body["storage_path"])
            # stored file really extracts
            text, count = extract_pdf_text(body["storage_path"])
            assert count == 2
            assert "upload page two" in text
        _cleanup(email, engine)
    finally:
        _teardown(engine)


def test_upload_corrupt_bytes_rejected_no_rows_created():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xrc_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        proj_id = _setup_space_project(client, headers)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.background_job import BackgroundJob
        from app.models.material import Material

        mats_before = db.query(Material).filter(Material.project_id == uuid.UUID(proj_id)).count()
        jobs_before = db.query(BackgroundJob).count()
        db.close()

        resp = client.post(
            f"/api/v1/projects/{proj_id}/materials",
            files={"file": ("evil.pdf", b"definitely not a pdf", "application/pdf")},
            headers=headers,
        )
        assert resp.status_code == 400

        db = Sess()
        assert db.query(Material).filter(Material.project_id == uuid.UUID(proj_id)).count() == mats_before
        assert db.query(BackgroundJob).count() == jobs_before
        db.close()
        _cleanup(email, engine)
    finally:
        _teardown(engine)


def test_upload_empty_file_rejected():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xre_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        proj_id = _setup_space_project(client, headers)
        resp = client.post(
            f"/api/v1/projects/{proj_id}/materials",
            files={"file": ("empty.pdf", b"", "application/pdf")},
            headers=headers,
        )
        assert resp.status_code == 400
        _cleanup(email, engine)
    finally:
        _teardown(engine)


def test_upload_octet_stream_valid_pdf_accepted():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"xro_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_and_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_task.delay.return_value = MagicMock(id="celery-o")
            proj_id = _setup_space_project(client, headers)
            data = _pdf_bytes(["octet stream body"])
            resp = client.post(
                f"/api/v1/projects/{proj_id}/materials",
                files={"file": ("doc.pdf", data, "application/octet-stream")},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
        _cleanup(email, engine)
    finally:
        _teardown(engine)
