import logging
import uuid

import httpx

from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.services import ai_usage_service, job_service
from app.services.document_extraction_service import extract_pages
from app.services.structure_extraction_service import (
    StructureExtractionError,
    extract_learning_objects,
    extract_topic_map,
    slice_topic_source,
)
from app.services.structure_persistence_service import persist_knowledge_map
from app.worker.celery_app import celery_app
from app.worker.tasks import get_task_session

logger = logging.getLogger(__name__)


def _retry_delay(exc: httpx.HTTPError, retries: int) -> int:
    """Backoff seconds: 429s are per-minute rate windows, so wait the window
    out (re-queued, worker not blocked); other errors retry fast."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 429:
        return 60 * (retries + 1)
    return 2 ** retries * 2


def _load_pages(material: Material) -> tuple[list[dict], int]:
    """Per-page texts for page-tagged extraction (Phase B).

    Re-reads the stored PDF (page boundaries are not kept in extracted_text);
    falls back to the stored blob as one pseudo-page so legacy/odd materials
    still map instead of failing.
    """
    try:
        pages = extract_pages(material.storage_path)
        numbered = [p for p in pages if (p.get("text") or "").strip()]
        if numbered:
            return pages, material.page_count or len(pages)
    except (FileNotFoundError, ValueError, OSError) as e:
        logger.warning("structure page re-read failed, using stored text: %s", e)
    blob = (material.extracted_text or "").strip()
    if not blob:
        return [], 0
    return [{"page_number": 1, "text": blob}], 1


@celery_app.task(name="build_structure", bind=True, max_retries=3)
def build_structure(self, job_id: str, material_id: str) -> dict:
    """Two-pass knowledge-map build for one material (Phase B).

    Pass 1 maps topics/subtopics (+ page spans); Pass 2 extracts classified
    learning objects per topic; persist is one atomic identity-preserving
    commit. Same lifecycle/backoff contract as before: provider failures fail
    only this job visibly — extraction, chunking, and embeddings are never
    rolled back because of it. A topic whose Pass 2 fails after retry is
    skipped (structure kept, reported in `failed_topics`) rather than failing
    the whole map.
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

        pages, page_count = _load_pages(material)
        if not pages or page_count <= 0:
            msg = "Material has no extracted text to map"
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                pass
            return {"status": "failed", "error": msg, "material_id": str(mid)}

        # Meter Pass 1 (PRD §14). Patched fakes in tests make no provider
        # calls → the tracker writes nothing.
        owner_id = ai_usage_service.resolve_owner_user_id(db, project_id=material.project_id)
        try:
            with ai_usage_service.track_llm_call(
                user_id=owner_id,
                project_id=material.project_id,
                feature=ai_usage_service.FEATURE_STRUCTURE_TOPIC_MAP,
                meta={"pages": page_count},
            ):
                topic_map = extract_topic_map(pages, page_count)
        except (StructureExtractionError, ValueError, RuntimeError) as e:
            msg = f"Structure extraction failed: {e}"[:1000]
            try:
                job_service.mark_failed(db, jid, msg)
            except Exception:
                pass
            return {"status": "failed", "error": msg, "material_id": str(mid)}
        except httpx.HTTPError as e:
            # NB: when retries are exhausted, self.retry() re-raises the
            # original error instead of MaxRetriesExceededError — count
            # attempts explicitly so the job is always marked failed.
            if self.request.retries >= 3:
                msg = f"Structure provider unavailable after retries: {e}"[:1000]
                try:
                    job_service.mark_failed(db, jid, msg)
                except Exception:
                    pass
                return {"status": "failed", "error": msg, "material_id": str(mid)}
            raise self.retry(exc=e, countdown=_retry_delay(e, self.request.retries), max_retries=3)

        # Pass 2 per topic; individual topic failures skip (reported), the
        # rest of the map still persists. LLM transport errors inside Pass 2
        # are per-topic: retried once inside the service, then skipped.
        topic_results = []
        failed_topics: list[str] = []
        for topic_span in topic_map.topics:
            source = slice_topic_source(pages, topic_span.page_start, topic_span.page_end)
            if not source.strip():
                failed_topics.append(topic_span.title)
                topic_results.append((topic_span, None))
                continue
            try:
                with ai_usage_service.track_llm_call(
                    user_id=owner_id,
                    project_id=material.project_id,
                    feature=ai_usage_service.FEATURE_STRUCTURE_OBJECTS,
                    meta={"topic": topic_span.title[:80]},
                ):
                    lo_result = extract_learning_objects(
                        topic_span.title,
                        [s.title for s in topic_span.subtopics],
                        source,
                        topic_span.page_start,
                        topic_span.page_end,
                    )
            except (StructureExtractionError, ValueError, RuntimeError) as e:
                logger.warning("Pass 2 failed for topic %r: %s", topic_span.title, e)
                failed_topics.append(topic_span.title)
                topic_results.append((topic_span, None))
                continue
            except httpx.HTTPError as e:
                # One topic's transport failure must not fail the whole map.
                logger.warning("Pass 2 transport error for topic %r: %s", topic_span.title, e)
                failed_topics.append(topic_span.title)
                topic_results.append((topic_span, None))
                continue
            topic_results.append((topic_span, lo_result))

        counts = persist_knowledge_map(
            db,
            project_id=material.project_id,
            material_id=material.id,
            topic_map=topic_map,
            topic_results=topic_results,
        )
        for note in counts.get("guideline_notes", []):
            logger.warning("CORE guideline: %s", note)
        try:
            job_service.mark_completed(db, jid)
        except Exception:
            db.refresh(job)
            if job.status != "completed":
                job.status = "completed"
                db.commit()
        return {
            "status": "completed",
            "material_id": str(mid),
            "failed_topics": failed_topics,
            **counts,
        }
    finally:
        db.close()
