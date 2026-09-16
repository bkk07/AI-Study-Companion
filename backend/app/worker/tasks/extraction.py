import logging
import uuid

from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.services import job_service
from app.services.chunking_service import chunk_pages, persist_chunks
from app.services.document_extraction_service import extract_pages, extract_pdf_text
from app.worker.celery_app import celery_app
from app.worker.tasks import get_task_session as _get_task_session

log = logging.getLogger(__name__)


@celery_app.task(name="process_pdf", bind=True, max_retries=3)
def process_pdf(self, job_id: str, material_id: str) -> dict:
    """
    Phase 23: PyMuPDF extraction worker.

    - Loads PDF from shared storage_path inside worker
    - Extracts text via PyMuPDF, persists to materials.extracted_text
    - Updates job pending→running→completed/failed + material pending→processing→ready/failed atomically
    - Idempotency: if material already processing with same job running, skip; re-run updates
    - Corrupt PDF → failed immediately (no retry); transient errors retry 3x with backoff
    """
    try:
        jid = uuid.UUID(job_id)
        mid = uuid.UUID(material_id)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid job/material id: {e}") from e

    db = _get_task_session()
    try:
        job = db.get(BackgroundJob, jid)
        material = db.get(Material, mid)
        if not job or not material:
            # Diagnosable, not silent — mark what exists as failed if possible
            if job and job.status in ("pending", "running"):
                try:
                    job_service.mark_failed(db, jid, "Job or material not found")
                except Exception:
                    pass
            raise ValueError("Job or material not found")

        # Idempotency guard: avoid double-enqueue racing itself
        if material.status == "processing" and job.status == "running":
            # Already being processed — check if this is a retry of same celery task?
            # If celery_task_id matches current request, continue; else skip
            if job.celery_task_id and job.celery_task_id != self.request.id:
                return {"status": "skipped", "reason": "already processing", "material_id": str(mid)}

        # pending → running / pending → processing (same transaction boundary)
        try:
            if job.status == "pending":
                job_service.mark_running(db, jid)
        except Exception:
            pass  # idempotent: already running is ok

        # Refresh material in this session
        db.refresh(material)
        material.status = "processing"
        material.error_message = None
        db.commit()
        db.refresh(material)
        db.refresh(job)

        # Extract (worker reads shared volume path)
        try:
            text, page_count = extract_pdf_text(material.storage_path)
        except ValueError as e:
            # Corrupt/empty PDF — do not retry, straight to failed
            msg = str(e)[:1000]
            material.status = "failed"
            material.error_message = msg
            material.extracted_text = None
            db.commit()
            try:
                # job may already be running → failed
                if job.status == "pending":
                    job_service.mark_running(db, jid)
                    db.refresh(job)
                job_service.mark_failed(db, jid, msg)
            except Exception:
                job.status = "failed"
                job.error = msg
                db.commit()
            return {"status": "failed", "error": msg, "material_id": str(mid)}
        except FileNotFoundError as e:
            msg = str(e)[:1000]
            material.status = "failed"
            material.error_message = msg
            db.commit()
            try:
                if job.status == "pending":
                    job_service.mark_running(db, jid)
                job_service.mark_failed(db, jid, msg)
            except Exception:
                pass
            return {"status": "failed", "error": msg, "material_id": str(mid)}
        except Exception as e:
            # Transient — retry 3x with backoff, then failed
            try:
                raise self.retry(exc=e, countdown=2 ** self.request.retries * 2, max_retries=3)
            except self.MaxRetriesExceededError:
                msg = f"Extraction failed after retries: {e}"[:1000]
                material.status = "failed"
                material.error_message = msg
                db.commit()
                try:
                    job_service.mark_failed(db, jid, msg)
                except Exception:
                    pass
                return {"status": "failed", "error": msg, "material_id": str(mid)}

        # Success — persist atomically: material ready + job completed
        material.extracted_text = text
        material.page_count = page_count
        material.status = "ready"
        material.error_message = None
        db.commit()
        db.refresh(material)

        try:
            job_service.mark_completed(db, jid)
        except Exception:
            # If job was already failed/completed edge, ensure completed
            db.refresh(job)
            if job.status != "completed":
                job.status = "completed"
                db.commit()

        chained = _chain_downstream(db, material)
        return {"status": "completed", "material_id": str(mid), "page_count": page_count, "chars": len(text), **chained}
    finally:
        db.close()


def _chain_downstream(db, material: Material) -> dict:
    """Continue the pipeline after extraction: chunk inline, then queue
    embeddings + structure. Every step is best-effort — extraction stays
    `completed` even when a downstream stage cannot run (broker down, no
    Groq key); failures are returned in the result dict, never raised.
    """
    out: dict = {"chunks": 0, "embed_job": None, "structure_job": None}

    # 1. Chunk inline — deterministic local code, no network.
    try:
        pages = extract_pages(material.storage_path)
        drafts = chunk_pages([p["text"] for p in pages])
        persist_chunks(db, material.project_id, material.id, drafts, source_name=material.filename)
        out["chunks"] = len(drafts)
    except Exception as e:
        log.exception("Chunking failed for material %s", material.id)
        out["chain_error"] = f"chunking failed: {e}"[:500]
        return out  # without chunks, embeddings/structure are pointless

    # 2. Queue embeddings + structure under their own jobs (lazy imports:
    # tasks package already imports this module at worker startup).
    try:
        from app.worker.tasks.embeddings import generate_embeddings
        from app.worker.tasks.structure import build_structure

        embed_job = job_service.create_job(db, job_type="generate_embeddings", material_id=material.id)
        struct_job = job_service.create_job(db, job_type="build_structure", material_id=material.id)
        out["embed_job"] = str(embed_job.id)
        out["structure_job"] = str(struct_job.id)
        try:
            generate_embeddings.delay(str(embed_job.id), str(material.id))
        except Exception as e:
            log.warning("Embeddings dispatch failed for material %s: %s", material.id, e)
            out["embed_dispatch"] = f"dispatch failed: {e}"[:200]
        try:
            build_structure.delay(str(struct_job.id), str(material.id))
        except Exception as e:
            log.warning("Structure dispatch failed for material %s: %s", material.id, e)
            out["structure_dispatch"] = f"dispatch failed: {e}"[:200]
    except Exception as e:
        log.exception("Downstream job creation failed for material %s", material.id)
        out["chain_error"] = f"downstream setup failed: {e}"[:500]
    return out
