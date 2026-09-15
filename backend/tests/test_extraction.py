import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF for generating test PDFs
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.services import job_service


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
    client = TestClient(app)
    return client, engine


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


def _make_pdf(path: str, texts: list[str]):
    doc = fitz.open()
    for t in texts:
        page = doc.new_page()
        page.insert_text((72, 72), t)
    doc.save(path)
    doc.close()


def test_service_extracts_per_page():
    from app.services.document_extraction_service import extract_pages, extract_pdf_text

    tmpdir = tempfile.mkdtemp(prefix="extract_")
    pdf_path = os.path.join(tmpdir, "sample.pdf")
    _make_pdf(pdf_path, ["Hello extraction page one", "Second page content here"])

    text, pages = extract_pdf_text(pdf_path)
    assert pages == 2
    assert "Hello extraction page one" in text
    assert "Second page content here" in text

    per_page = extract_pages(pdf_path)
    assert len(per_page) == 2
    assert per_page[0]["page_number"] == 1
    assert "Hello extraction" in per_page[0]["text"]
    assert per_page[1]["page_number"] == 2


def test_task_success_persists_and_completes_job():
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"ex_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        # setup space/project via API (upload dispatch mocked to avoid real broker race)
        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "mock-celery-id"
            mock_task.delay.return_value = mock_result
            resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
            space_id = resp.json()["id"]
            resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "P"}, headers=headers)
            proj_id = resp.json()["id"]
            # create real PDF on disk for task (not via upload, to control path)
            pdf_path = os.path.join(tmpdir, proj_id, "real.pdf")
            Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
            _make_pdf(pdf_path, ["Extraction persistence check"])

        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.material import Material

        mat = Material(project_id=uuid.UUID(proj_id), filename="real.pdf", storage_path=pdf_path, status="pending")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
        mid, jid = str(mat.id), str(job.id)
        db.close()

        # run task synchronously (host can read tmpdir)
        result = process_pdf.apply(args=[jid, mid]).get()
        assert result["status"] == "completed"
        assert result["page_count"] == 1

        # verify DB: material ready + text, job completed
        Sess = sessionmaker(bind=engine)
        db2 = Sess()
        mat2 = db2.get(Material, uuid.UUID(mid))
        assert mat2.status == "ready"
        assert mat2.page_count == 1
        assert "Extraction persistence check" in (mat2.extracted_text or "")
        assert mat2.error_message is None
        job2 = job_service.get_job(db2, uuid.UUID(jid))
        assert job2.status == "completed"
        db2.close()

        # API visibility: GET job shows completed (ownership ok)
        resp = client.get(f"/api/v1/jobs/{jid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        # idempotent re-run: second apply still completes, no duplicates (same row updated)
        result2 = process_pdf.apply(args=[jid, mid]).get()
        # second run: job is already completed → mark_completed idempotent? Our task marks running first,
        # but completed→running is invalid → task handles? Let's check: task tries mark_running only if pending,
        # so second run keeps job completed then mark_completed idempotent same-status ok
        # Actually job.status is completed, task will skip mark_running (only if pending), then succeed and mark_completed (same-status allowed)
        assert result2["status"] == "completed"

        _cleanup(email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)


def test_task_failure_marks_failed_with_error():
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"exf_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}
        with patch("app.api.v1.materials.process_pdf"):
            resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
            space_id = resp.json()["id"]
            resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "P"}, headers=headers)
            proj_id = resp.json()["id"]

        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.material import Material

        # corrupt file
        bad_path = os.path.join(tmpdir, "bad.pdf")
        Path(bad_path).write_bytes(b"not a pdf at all")
        mat = Material(project_id=uuid.UUID(proj_id), filename="bad.pdf", storage_path=bad_path, status="pending")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
        bad_mid, bad_jid = str(mat.id), str(job.id)
        db.close()

        result = process_pdf.apply(args=[bad_jid, bad_mid]).get()
        assert result["status"] == "failed"
        assert "error" in result

        Sess = sessionmaker(bind=engine)
        db2 = Sess()
        mat2 = db2.get(Material, uuid.UUID(bad_mid))
        assert mat2.status == "failed"
        assert mat2.error_message is not None
        assert mat2.extracted_text is None
        job2 = job_service.get_job(db2, uuid.UUID(bad_jid))
        assert job2.status == "failed"
        assert job2.error is not None
        db2.close()

        # missing file also fails diagnosably
        Sess = sessionmaker(bind=engine)
        db3 = Sess()
        mat3 = Material(
            project_id=uuid.UUID(proj_id),
            filename="missing.pdf",
            storage_path=os.path.join(tmpdir, "does-not-exist.pdf"),
            status="pending",
        )
        db3.add(mat3)
        db3.commit()
        db3.refresh(mat3)
        job3 = job_service.create_job(db3, job_type="process_pdf", material_id=mat3.id)
        miss_mid, miss_jid = str(mat3.id), str(job3.id)
        db3.close()
        result3 = process_pdf.apply(args=[miss_jid, miss_mid]).get()
        assert result3["status"] == "failed"

        _cleanup(email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)


def test_upload_creates_job_and_dispatches():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"exu_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
        space_id = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "P"}, headers=headers)
        proj_id = resp.json()["id"]

        # patch delay to avoid real broker, verify dispatch called + job created
        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "celery-123"
            mock_task.delay.return_value = mock_result
            # need real PDF bytes with %PDF header (minimal, PyMuPDF may fail but upload only checks header)
            pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
            resp = client.post(
                f"/api/v1/projects/{proj_id}/materials",
                files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            assert mock_task.delay.called
            args, _ = mock_task.delay.call_args
            assert len(args) == 2  # job_id, material_id
            material_id = resp.json()["id"]
            assert args[1] == material_id

            # job row exists pending (or running) with celery_task_id
            Sess = sessionmaker(bind=engine)
            db = Sess()
            from app.models.background_job import BackgroundJob

            jobs = db.query(BackgroundJob).filter(BackgroundJob.material_id == uuid.UUID(material_id)).all()
            assert len(jobs) == 1
            assert jobs[0].job_type == "process_pdf"
            assert jobs[0].celery_task_id == "celery-123"
            db.close()

        _cleanup(email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)
