import uuid

import httpx

from app.models.background_job import BackgroundJob
from app.models.chunk import DocumentChunk
from app.models.embedding import EMBEDDING_DIMS, Embedding
from app.models.material import Material
from app.services import job_service
from app.services.ai import embedding_client
from app.worker.celery_app import celery_app
from app.worker.tasks import get_task_session


def _retry_delay(exc: httpx.HTTPError, retries: int) -> int:
    """429s are per-minute rate windows — wait them out (re-queued, worker not
    blocked); anything else retries fast."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 429:
        return 60 * (retries + 1)
    return 2 ** retries * 2


@celery_app.task(name="generate_embeddings", bind=True, max_retries=3)
def generate_embeddings(self, job_id: str, material_id: str) -> dict:
    """
    Phase 29: chunk → embed → store vectors.

    - Reads the material's chunks ordered by chunk_index
    - Embeds contents in one batched client call (mockable)
    - Upserts one Embedding per chunk_id: re-runs never duplicate rows
    - Job pending→running→completed/failed; transient HTTP errors retry 3x
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

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.material_id == mid)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            msg = "No chunks found for material"
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                job.status = "failed"
                job.error = msg
                db.commit()
            return {"status": "failed", "error": msg, "material_id": str(mid)}

        try:
            vectors = embedding_client.embed([c.content for c in chunks])
        except ValueError as e:
            msg = str(e)[:1000]
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                job.status = "failed"
                job.error = msg
                db.commit()
            return {"status": "failed", "error": msg, "material_id": str(mid)}
        except httpx.HTTPError as e:
            # Same guard as build_structure: retry() re-raises the original
            # error once exhausted, so count attempts explicitly.
            if self.request.retries >= 3:
                msg = f"Embedding failed after retries: {e}"[:1000]
                try:
                    job_service.mark_failed(db, jid, msg)
                except Exception:
                    pass
                return {"status": "failed", "error": msg, "material_id": str(mid)}
            raise self.retry(exc=e, countdown=_retry_delay(e, self.request.retries), max_retries=3)

        dims = {len(v) for v in vectors}
        if len(vectors) != len(chunks) or dims != {EMBEDDING_DIMS}:
            msg = f"Embedding client returned {len(vectors)} vectors with dims {sorted(dims)}, expected {len(chunks)}x{EMBEDDING_DIMS}"
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                job.status = "failed"
                job.error = msg
                db.commit()
            return {"status": "failed", "error": msg, "material_id": str(mid)}

        # Upsert one row per exact chunk — retries update, never duplicate.
        for chunk, vector in zip(chunks, vectors):
            row = db.query(Embedding).filter(Embedding.chunk_id == chunk.id).first()
            if row is None:
                db.add(
                    Embedding(
                        project_id=material.project_id,
                        material_id=mid,
                        chunk_id=chunk.id,
                        embedding=vector,
                    )
                )
            else:
                row.embedding = vector
        db.commit()

        try:
            job_service.mark_completed(db, jid)
        except Exception:
            db.refresh(job)
            if job.status != "completed":
                job.status = "completed"
                db.commit()

        return {"status": "completed", "material_id": str(mid), "chunks": len(chunks), "dims": EMBEDDING_DIMS}
    finally:
        db.close()
