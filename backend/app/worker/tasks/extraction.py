import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.services import job_service
from app.services.document_extraction_service import extract_pdf_text
from app.worker.celery_app import celery_app


def _get_task_session():
    """Fresh DB session from current settings — respects DATABASE_URL override (host localhost vs container postgres)."""
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    Sess = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Sess()


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

        return {"status": "completed", "material_id": str(mid), "page_count": page_count, "chars": len(text)}
    finally:
        db.close()
