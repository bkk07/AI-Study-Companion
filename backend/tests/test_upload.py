import os
import tempfile
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


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


def _register_and_login(client: TestClient, email: str, pwd: str = "supersecret123") -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _cleanup(client: TestClient, email: str, engine):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()


MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def test_upload_valid_pdf():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"up_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        # create space + project
        resp = client.post("/api/v1/spaces", json={"name": "UpSpace"}, headers=headers)
        space_id = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "UpProj"}, headers=headers)
        project_id = resp.json()["id"]

        # valid PDF upload
        resp = client.post(
            f"/api/v1/projects/{project_id}/materials",
            files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["filename"] == "doc.pdf"
        assert data["project_id"] == project_id
        assert data["status"] == "pending"
        assert "storage_path" in data
        # server-controlled path
        assert project_id in data["storage_path"]
        assert data["storage_path"].startswith(tmpdir) or tmpdir in data["storage_path"]

        # file exists on disk
        import os as _os

        assert _os.path.exists(data["storage_path"])
        assert open(data["storage_path"], "rb").read().startswith(b"%PDF")

        # list materials
        resp = client.get(f"/api/v1/projects/{project_id}/materials", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        _cleanup(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)


def test_upload_rejects_non_pdf_and_oversized():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"up2_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
        space_id = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "P"}, headers=headers)
        project_id = resp.json()["id"]

        # non-PDF extension
        resp = client.post(
            f"/api/v1/projects/{project_id}/materials",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 400, resp.text

        # PDF extension but invalid header
        resp = client.post(
            f"/api/v1/projects/{project_id}/materials",
            files={"file": ("doc.pdf", b"not a pdf", "application/pdf")},
            headers=headers,
        )
        assert resp.status_code == 400, resp.text

        # wrong content_type with pdf magic still rejected via content_type check
        resp = client.post(
            f"/api/v1/projects/{project_id}/materials",
            files={"file": ("doc.pdf", MINIMAL_PDF, "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 400, resp.text

        # oversized: patch limit to 10 bytes to avoid 10MB payload
        from app.services import storage_service

        orig = storage_service.MAX_PDF_BYTES
        storage_service.MAX_PDF_BYTES = 10
        try:
            resp = client.post(
                f"/api/v1/projects/{project_id}/materials",
                files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
                headers=headers,
            )
            assert resp.status_code == 413, resp.text
        finally:
            storage_service.MAX_PDF_BYTES = orig

        _cleanup(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)


def test_upload_isolation_and_auth():
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email_a = f"a_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"b_{uuid.uuid4().hex[:8]}@example.com"
        token_a = _register_and_login(client, email_a)
        token_b = _register_and_login(client, email_b)
        h_a = {"Authorization": f"Bearer {token_a}"}
        h_b = {"Authorization": f"Bearer {token_b}"}

        resp = client.post("/api/v1/spaces", json={"name": "AS"}, headers=h_a)
        space_a = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_a}/projects", json={"name": "AP"}, headers=h_a)
        proj_a = resp.json()["id"]

        # B cannot upload to A's project
        resp = client.post(
            f"/api/v1/projects/{proj_a}/materials",
            files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
            headers=h_b,
        )
        assert resp.status_code in (403, 404), resp.text

        # no token -> 401
        resp = client.post(
            f"/api/v1/projects/{proj_a}/materials",
            files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert resp.status_code == 401

        # path traversal filename sanitized: storage should not contain ..
        resp = client.post(
            f"/api/v1/projects/{proj_a}/materials",
            files={"file": ("../../evil.pdf", MINIMAL_PDF, "application/pdf")},
            headers=h_a,
        )
        assert resp.status_code == 201, resp.text
        assert ".." not in resp.json()["storage_path"]
        assert resp.json()["filename"] == "evil.pdf"

        _cleanup(client, email_a, engine)
        _cleanup(client, email_b, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("UPLOAD_DIR", None)
