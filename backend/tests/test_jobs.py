import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

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


MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def test_job_lifecycle_transitions():
    # direct job_service lifecycle without HTTP
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        from app.db.session import get_db as _get_db  # noqa: F401
        Sess = sessionmaker(bind=engine)
        db = Sess()
        # create generic job
        job = job_service.create_job(db, job_type="ping")
        assert job.status == "pending"
        assert job.job_type == "ping"
        # pending→running
        job = job_service.mark_running(db, job.id)
        assert job.status == "running"
        # running→completed
        job = job_service.mark_completed(db, job.id)
        assert job.status == "completed"
        # completed→running should fail 400
        try:
            job_service.mark_running(db, job.id)
            assert False, "should have raised invalid transition"
        except Exception as e:
            # fastapi HTTPException
            assert "Invalid transition" in str(e)

        # failed path with error
        job2 = job_service.create_job(db, job_type="extraction")
        job2 = job_service.mark_running(db, job2.id)
        job2 = job_service.mark_failed(db, job2.id, error="boom failed")
        assert job2.status == "failed"
        assert job2.error == "boom failed"

        # failed→completed should fail
        try:
            job_service.mark_completed(db, job2.id)
            assert False
        except Exception as e:
            assert "Invalid transition" in str(e)

        # cleanup
        db.query(job_service.BackgroundJob if hasattr(job_service, "BackgroundJob") else db.query(job_service.get_job(db, job.id).__class__)).filter_by(id=job.id).delete()  # fallback cleanup via raw
        from app.models.background_job import BackgroundJob

        db.query(BackgroundJob).filter(BackgroundJob.id.in_([job.id, job2.id])).delete(synchronize_session=False)
        db.commit()
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)


def test_jobs_api_isolation():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email_a = f"ja_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"jb_{uuid.uuid4().hex[:8]}@example.com"
        token_a = _register_and_login(client, email_a)
        token_b = _register_and_login(client, email_b)
        h_a = {"Authorization": f"Bearer {token_a}"}
        h_b = {"Authorization": f"Bearer {token_b}"}

        # A creates space/project/material to get a material-owned job (dispatch mocked)
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=h_a)
        space_a = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_a}/projects", json={"name": "P"}, headers=h_a)
        proj_a = resp.json()["id"]
        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_task.delay.return_value = MagicMock(id="mock-id")
            resp = client.post(
                f"/api/v1/projects/{proj_a}/materials",
                files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
                headers=h_a,
            )
        assert resp.status_code == 201, resp.text
        material_a = resp.json()["id"]

        # create job via service tied to that material (simulate dispatch)
        Sess = sessionmaker(bind=engine)
        db = Sess()
        job = job_service.create_job(db, job_type="extraction", material_id=uuid.UUID(material_a))
        db.close()
        job_id = str(job.id)

        # own succeeds
        resp = client.get(f"/api/v1/jobs/{job_id}", headers=h_a)
        assert resp.status_code == 200, resp.text
        assert resp.json()["job_type"] == "extraction"

        # status transition via service should reflect in GET
        Sess = sessionmaker(bind=engine)
        db2 = Sess()
        job_service.mark_running(db2, uuid.UUID(job_id))
        db2.close()
        resp = client.get(f"/api/v1/jobs/{job_id}", headers=h_a)
        assert resp.json()["status"] == "running"

        # foreign user cannot see
        resp = client.get(f"/api/v1/jobs/{job_id}", headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        # no token -> 401
        resp = client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 401

        # mark completed then GET should show completed
        Sess = sessionmaker(bind=engine)
        db3 = Sess()
        job_service.mark_completed(db3, uuid.UUID(job_id))
        db3.close()
        resp = client.get(f"/api/v1/jobs/{job_id}", headers=h_a)
        assert resp.json()["status"] == "completed"

        # cleanup job
        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.background_job import BackgroundJob

        db.query(BackgroundJob).filter(BackgroundJob.id == uuid.UUID(job_id)).delete()
        db.commit()
        db.close()

        # generic jobs without material carry no ownership — must be hidden (404)
        Sess = sessionmaker(bind=engine)
        db = Sess()
        job_generic = job_service.create_job(db, job_type="ping")
        db.close()
        resp = client.get(f"/api/v1/jobs/{str(job_generic.id)}", headers=h_a)
        assert resp.status_code == 404
        # cleanup generic
        Sess = sessionmaker(bind=engine)
        db = Sess()
        db.query(BackgroundJob).filter(BackgroundJob.id == job_generic.id).delete()
        db.commit()
        db.close()

        _cleanup(email_a, engine)
        _cleanup(email_b, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)
