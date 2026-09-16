import uuid

import httpx

from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.services import job_service
from app.services.structure_extraction_service import StructureExtractionError, extract_structure
from app.services.structure_persistence_service import persist_structure
from app.worker.celery_app import celery_app
from app.worker.tasks import get_task_session


@celery_app.task(name="build_structure", bind=True, max_retries=3)
def build_structure(self, job_id: str, material_id: str) -> dict:
    """Extract + persist the Topic → Subtopic → Concept map for one material.

    Dispatched by `process_pdf` after extraction. Groq failures (including a
    missing key) fail only this job with a visible message — extraction,
    chunking, and embeddings are never rolled back because of it.
    """
    try:
        jid = uuid.UUID(job_id)
        mid = uuid.UUID(material_id)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid job/material id: {e}") from e

    db = get_task_session()
    try:
        job = db.get(BackgroundJob, jid)
        material = db.get(Material, mid)
        if not job or not material:
            if job and job.status in ("pending", "running"):
                try:
                    job_service.mark_failed(db, jid, "Job or material not found")
                except Exception:
                    pass
            raise ValueError("Job or material not found")

        if job.status == "pending":
            try:
                job_service.mark_running(db, jid)
            except Exception:
                pass  # idempotent: already running is ok

        if not (material.extracted_text or "").strip():
            msg = "Material has no extracted text to map"
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                pass
            return {"status": "failed", "error": msg, "material_id": str(mid)}

        try:
            outline = extract_structure(material.extracted_text)
        except (StructureExtractionError, ValueError, RuntimeError) as e:
            msg = f"Structure extraction failed: {e}"[:1000]
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                pass
            return {"status": "failed", "error": msg, "material_id": str(mid)}
        except httpx.HTTPError as e:
            try:
                raise self.retry(exc=e, countdown=2 ** self.request.retries * 2, max_retries=3)
            except self.MaxRetriesExceededError:
                msg = f"Structure provider unavailable after retries: {e}"[:1000]
                try:
                    job_service.mark_failed(db, jid, msg)
                except Exception:
                    pass
                return {"status": "failed", "error": msg, "material_id": str(mid)}

        counts = persist_structure(db, material.project_id, outline)
        try:
            job_service.mark_completed(db, jid)
        except Exception:
            db.refresh(job)
            if job.status != "completed":
                job.status = "completed"
                db.commit()
        return {"status": "completed", "material_id": str(mid), **counts}
    finally:
        db.close()
