import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.embedding import EMBEDDING_DIMS, Embedding
from app.services import job_service
from app.services.chunking_service import chunk_text, persist_chunks

DIMS = EMBEDDING_DIMS


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


def _teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()
    os.environ.pop("UPLOAD_DIR", None)


def _register_login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _seed_material_with_chunks(client: TestClient, headers: dict, engine, n_chars: int = 4500):
    from app.models.material import Material

    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
    sid = resp.json()["id"]
    resp = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers)
    pid = resp.json()["id"]

    Sess = sessionmaker(bind=engine)
    db = Sess()
    mat = Material(project_id=uuid.UUID(pid), filename="doc.pdf", storage_path="/tmp/doc.pdf", status="ready")
    db.add(mat)
    db.commit()
    db.refresh(mat)
    mid = mat.id
    text = ("retrieval content words for embedding tests " * ((n_chars // 45) + 1))[:n_chars].rstrip()
    drafts = chunk_text(text)
    persist_chunks(db, uuid.UUID(pid), mid, drafts, source_name="doc.pdf")
    job = job_service.create_job(db, job_type="generate_embeddings", material_id=mid)
    jid = job.id
    db.close()
    return str(pid), str(mid), str(jid), len(drafts)


def _vec(marker: float) -> list[float]:
    v = [0.0] * DIMS
    v[0] = marker
    return v


def test_task_success_stores_vectors_and_completes():
    from app.worker.tasks.embeddings import generate_embeddings

    tmpdir = __import__("tempfile").mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"em_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            pid, mid, jid, n = _seed_material_with_chunks(client, headers, engine)

        with patch("app.worker.tasks.embeddings.embedding_client") as mock_client:
            mock_client.embed.return_value = [_vec(float(i + 1)) for i in range(n)]
            result = generate_embeddings.apply(args=[jid, mid]).get()

        assert result["status"] == "completed"
        assert result["chunks"] == n
        assert result["dims"] == DIMS
        mock_client.embed.assert_called_once()
        assert len(mock_client.embed.call_args[0][0]) == n

        Sess = sessionmaker(bind=engine)
        db = Sess()
        rows = db.query(Embedding).filter(Embedding.material_id == uuid.UUID(mid)).all()
        assert len(rows) == n
        assert all(r.project_id == uuid.UUID(pid) for r in rows)
        assert sorted(r.embedding[0] for r in rows) == [float(i + 1) for i in range(n)]
        assert all(len(r.embedding) == DIMS for r in rows)
        assert job_service.get_job(db, uuid.UUID(jid)).status == "completed"
        # chunk linkage exact: one embedding per chunk
        from app.models.chunk import DocumentChunk

        chunk_ids = {c.id for c in db.query(DocumentChunk).filter(DocumentChunk.material_id == uuid.UUID(mid)).all()}
        assert {r.chunk_id for r in rows} == chunk_ids
        db.close()

        # cleanup
        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        _teardown(engine)


def test_task_rerun_stable_count_updates_values():
    from app.worker.tasks.embeddings import generate_embeddings

    tmpdir = __import__("tempfile").mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"emr_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            _, mid, jid, n = _seed_material_with_chunks(client, headers, engine)

        with patch("app.worker.tasks.embeddings.embedding_client") as mock_client:
            mock_client.embed.return_value = [_vec(1.0) for _ in range(n)]
            assert generate_embeddings.apply(args=[jid, mid]).get()["status"] == "completed"
            mock_client.embed.return_value = [_vec(9.0) for _ in range(n)]
            result2 = generate_embeddings.apply(args=[jid, mid]).get()
            assert result2["status"] == "completed"

        Sess = sessionmaker(bind=engine)
        db = Sess()
        rows = db.query(Embedding).filter(Embedding.material_id == uuid.UUID(mid)).all()
        assert len(rows) == n  # no duplicates
        assert all(r.embedding[0] == 9.0 for r in rows)  # values updated
        db.close()

        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        _teardown(engine)


def test_task_client_error_fails_diagnosably():
    from app.worker.tasks.embeddings import generate_embeddings

    tmpdir = __import__("tempfile").mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"emf_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            _, mid, jid, _ = _seed_material_with_chunks(client, headers, engine)

        with patch("app.worker.tasks.embeddings.embedding_client") as mock_client:
            mock_client.embed.side_effect = ValueError("bad client output")
            result = generate_embeddings.apply(args=[jid, mid]).get()

        assert result["status"] == "failed"
        assert "bad client output" in result["error"]
        Sess = sessionmaker(bind=engine)
        db = Sess()
        assert db.query(Embedding).filter(Embedding.material_id == uuid.UUID(mid)).count() == 0
        assert job_service.get_job(db, uuid.UUID(jid)).status == "failed"
        db.close()

        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        _teardown(engine)


def test_task_no_chunks_fails():
    from app.models.material import Material
    from app.worker.tasks.embeddings import generate_embeddings

    tmpdir = __import__("tempfile").mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"emn_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
            sid = resp.json()["id"]
            pid = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers).json()["id"]

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = Material(project_id=uuid.UUID(pid), filename="x.pdf", storage_path="/tmp/x.pdf", status="ready")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="generate_embeddings", material_id=mat.id)
        mid, jid = str(mat.id), str(job.id)
        db.close()

        result = generate_embeddings.apply(args=[jid, mid]).get()
        assert result["status"] == "failed"
        assert "No chunks" in result["error"]

        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        _teardown(engine)


def test_task_missing_rows_failed_then_raise():
    from app.worker.tasks.embeddings import generate_embeddings

    tmpdir = __import__("tempfile").mkdtemp(prefix="uploads_")
    client, engine = _override_and_client(tmpdir)
    try:
        email = f"emx_{uuid.uuid4().hex[:8]}@example.com"
        headers = {"Authorization": f"Bearer {_register_login(client, email)}"}
        with patch("app.api.v1.materials.process_pdf"):
            resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
            sid = resp.json()["id"]
            pid = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers).json()["id"]

        Sess = sessionmaker(bind=engine)
        db = Sess()
        from app.models.material import Material

        mat = Material(project_id=uuid.UUID(pid), filename="y.pdf", storage_path="/tmp/y.pdf", status="ready")
        db.add(mat)
        db.commit()
        db.refresh(mat)
        job = job_service.create_job(db, job_type="generate_embeddings", material_id=mat.id)
        jid = str(job.id)
        db.close()

        with pytest.raises(ValueError, match="not found"):
            generate_embeddings.apply(args=[jid, str(uuid.uuid4())]).get()

        db = Sess()
        assert job_service.get_job(db, uuid.UUID(jid)).status == "failed"
        db.close()

        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        _teardown(engine)
