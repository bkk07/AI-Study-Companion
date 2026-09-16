"""Pipeline chain: extraction → chunk → embed/structure jobs (real PG)."""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from celery.exceptions import Retry

import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.background_job import BackgroundJob
from app.models.chunk import DocumentChunk
from app.models.material import Material
from app.schemas.structure import StructureOutline
from app.services import job_service


def _setup(tmpdir):
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
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


def _login(client, email):
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _project(client, headers):
    sid = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers).json()["id"]
    return client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers).json()["id"]


def _make_pdf(path, pages):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def _material_job(engine, tmpdir, proj_id, words):
    pdf_path = os.path.join(tmpdir, proj_id, "chain.pdf")
    _make_pdf(pdf_path, [" ".join(words)])
    Sess = sessionmaker(bind=engine)
    db = Sess()
    mat = Material(project_id=uuid.UUID(proj_id), filename="chain.pdf", storage_path=pdf_path, status="pending")
    db.add(mat)
    db.commit()
    db.refresh(mat)
    job = job_service.create_job(db, job_type="process_pdf", material_id=mat.id)
    mid, jid = str(mat.id), str(job.id)
    db.close()
    return mid, jid


def test_extraction_chains_chunks_and_downstream_jobs():
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="chain_")
    client, engine = _setup(tmpdir)
    try:
        h = _login(client, f"ch_{uuid.uuid4().hex[:8]}@example.com")
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _project(client, h)
        mid, jid = _material_job(engine, tmpdir, proj_id, ["photosynthesis converts light energy"] * 40)

        with (
            patch("app.worker.tasks.embeddings.generate_embeddings") as mock_emb,
            patch("app.worker.tasks.structure.build_structure") as mock_struct,
        ):
            result = process_pdf.apply(args=[jid, mid]).get()

        assert result["status"] == "completed", result
        assert result["chunks"] >= 1
        assert result["embed_job"] and result["structure_job"]
        mock_emb.delay.assert_called_once_with(result["embed_job"], mid)
        mock_struct.delay.assert_called_once_with(result["structure_job"], mid)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            assert db.query(DocumentChunk).filter(DocumentChunk.material_id == uuid.UUID(mid)).count() >= 1
            jobs = {j.job_type: j.status for j in db.query(BackgroundJob).filter(BackgroundJob.material_id == uuid.UUID(mid)).all()}
            assert jobs.get("generate_embeddings") == "pending"
            assert jobs.get("build_structure") == "pending"
        finally:
            db.close()
    finally:
        _teardown(engine)


def test_chain_survives_broker_outage():
    from app.worker.tasks.extraction import process_pdf

    tmpdir = tempfile.mkdtemp(prefix="chain_")
    client, engine = _setup(tmpdir)
    try:
        h = _login(client, f"chb_{uuid.uuid4().hex[:8]}@example.com")
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _project(client, h)
        mid, jid = _material_job(engine, tmpdir, proj_id, ["mitochondria produce energy"] * 40)

        with (
            patch("app.worker.tasks.embeddings.generate_embeddings") as mock_emb,
            patch("app.worker.tasks.structure.build_structure") as mock_struct,
        ):
            mock_emb.delay.side_effect = ConnectionError("broker down")
            mock_struct.delay.side_effect = ConnectionError("broker down")
            result = process_pdf.apply(args=[jid, mid]).get()

        assert result["status"] == "completed", result  # extraction stands on its own
        assert result["chunks"] >= 1
        assert "dispatch failed" in result["embed_dispatch"]
        assert "dispatch failed" in result["structure_dispatch"]
    finally:
        _teardown(engine)


def _outline():
    return StructureOutline.model_validate(
        {"topics": [{"title": "T", "subtopics": [{"title": "S", "concepts": [{"title": "C", "summary": "sum"}]}]}]}
    )


def _topic_map():
    from app.schemas.structure import TopicMapOutline

    return TopicMapOutline.model_validate(
        {"topics": [{"title": "T", "page_start": 1, "page_end": 1,
                     "subtopics": [{"title": "S", "page_start": 1, "page_end": 1}]}]}
    )


def _topic_los():
    from app.schemas.structure import TopicLearningObjects

    return TopicLearningObjects.model_validate(
        {"objects": [{"name": "C", "subtopic": "S", "type": "CONCEPT",
                      "importance": "CORE", "summary": "sum",
                      "page_start": 1, "page_end": 1}]}
    )


def test_build_structure_success_persists_map():
    from app.models.topic import Topic
    from app.worker.tasks.structure import build_structure

    tmpdir = tempfile.mkdtemp(prefix="chain_")
    client, engine = _setup(tmpdir)
    try:
        h = _login(client, f"chs_{uuid.uuid4().hex[:8]}@example.com")
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _project(client, h)
        mid, _ = _material_job(engine, tmpdir, proj_id, ["content"] * 20)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = db.get(Material, uuid.UUID(mid))
        mat.extracted_text = "Some study text about cells."
        mat.status = "ready"
        db.commit()
        sjob = job_service.create_job(db, job_type="build_structure", material_id=uuid.UUID(mid))
        sjid = str(sjob.id)
        db.close()

        with (
            patch("app.worker.tasks.structure.extract_topic_map", return_value=_topic_map()),
            patch("app.worker.tasks.structure.extract_learning_objects", return_value=_topic_los()),
        ):
            result = build_structure.apply(args=[sjid, mid]).get()

        assert result["status"] == "completed", result
        assert result["concepts"] == 1
        assert result["failed_topics"] == []
        db = Sess()
        try:
            assert db.query(Topic).filter(Topic.project_id == uuid.UUID(proj_id)).count() == 1
            assert job_service.get_job(db, uuid.UUID(sjid)).status == "completed"
        finally:
            db.close()
    finally:
        _teardown(engine)


def test_retry_exhaustion_marks_job_failed_not_stuck():
    """Groq 429s past max retries must fail the job visibly (regression:
    retry() re-raises the original error, which used to escape and leave
    the job `running` forever)."""
    import httpx

    from app.worker.tasks.structure import build_structure

    tmpdir = tempfile.mkdtemp(prefix="chain_")
    client, engine = _setup(tmpdir)
    try:
        h = _login(client, f"chr_{uuid.uuid4().hex[:8]}@example.com")
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _project(client, h)
        mid, _ = _material_job(engine, tmpdir, proj_id, ["content"] * 20)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = db.get(Material, uuid.UUID(mid))
        mat.extracted_text = "Some study text."
        mat.status = "ready"
        db.commit()
        sjob = job_service.create_job(db, job_type="build_structure", material_id=uuid.UUID(mid))
        sjid = str(sjob.id)
        db.close()

        with patch(
            "app.worker.tasks.structure.extract_topic_map",
            side_effect=httpx.ConnectError("provider down"),
        ):
            build_structure.push_request(args=[sjid, mid], retries=3)
            try:
                result = build_structure.run(sjid, mid)
            finally:
                build_structure.pop_request()

        assert result["status"] == "failed", result
        assert "retries" in result["error"]
        db = Sess()
        try:
            assert job_service.get_job(db, uuid.UUID(sjid)).status == "failed"
        finally:
            db.close()
    finally:
        _teardown(engine)


def _http_error(status: int) -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return httpx.HTTPStatusError(f"{status} test", request=req, response=httpx.Response(status, request=req))


def test_retry_delay_waits_out_rate_windows():
    from app.worker.tasks import embeddings as emb_tasks
    from app.worker.tasks import structure as struct_tasks

    for mod in (emb_tasks, struct_tasks):
        assert mod._retry_delay(_http_error(429), 0) == 60
        assert mod._retry_delay(_http_error(429), 2) == 180
        assert mod._retry_delay(_http_error(500), 0) == 2
        assert mod._retry_delay(_http_error(503), 1) == 4
        assert mod._retry_delay(httpx.ConnectError("down"), 0) == 2


def test_structure_429_schedules_minute_backoff_not_fast_retry():
    from app.worker.tasks.structure import build_structure

    tmpdir = tempfile.mkdtemp(prefix="chain_")
    client, engine = _setup(tmpdir)
    try:
        h = _login(client, f"cb_{uuid.uuid4().hex[:8]}@example.com")
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _project(client, h)
        mid, _ = _material_job(engine, tmpdir, proj_id, ["content"] * 20)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = db.get(Material, uuid.UUID(mid))
        mat.extracted_text = "Some study text."
        mat.status = "ready"
        db.commit()
        sjob = job_service.create_job(db, job_type="build_structure", material_id=uuid.UUID(mid))
        sjid = str(sjob.id)
        db.close()

        with (
            patch("app.worker.tasks.structure.extract_topic_map", side_effect=_http_error(429)),
            patch.object(build_structure, "retry", side_effect=Retry()) as mock_retry,
        ):
            build_structure.push_request(args=[sjid, mid], retries=0)
            try:
                with pytest.raises(Retry):
                    build_structure.run(sjid, mid)
            finally:
                build_structure.pop_request()
        assert mock_retry.call_count == 1
        assert mock_retry.call_args.kwargs["countdown"] == 60
    finally:
        _teardown(engine)


def test_build_structure_failure_fails_only_its_job():
    from app.worker.tasks.structure import build_structure

    tmpdir = tempfile.mkdtemp(prefix="chain_")
    client, engine = _setup(tmpdir)
    try:
        h = _login(client, f"chf_{uuid.uuid4().hex[:8]}@example.com")
        with patch("app.api.v1.materials.process_pdf"):
            proj_id = _project(client, h)
        mid, _ = _material_job(engine, tmpdir, proj_id, ["content"] * 20)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        mat = db.get(Material, uuid.UUID(mid))
        mat.extracted_text = "Some study text."
        mat.status = "ready"
        db.commit()
        sjob = job_service.create_job(db, job_type="build_structure", material_id=uuid.UUID(mid))
        sjid = str(sjob.id)
        db.close()

        with patch("app.worker.tasks.structure.extract_topic_map", side_effect=RuntimeError("INCEPTION_API_KEY is not configured")):
            result = build_structure.apply(args=[sjid, mid]).get()

        assert result["status"] == "failed", result
        assert "INCEPTION_API_KEY" in result["error"]
        db = Sess()
        try:
            assert job_service.get_job(db, uuid.UUID(sjid)).status == "failed"
            assert db.get(Material, uuid.UUID(mid)).status == "ready"  # extraction untouched
        finally:
            db.close()
    finally:
        _teardown(engine)
