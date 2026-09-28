import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.core.config import get_settings
from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.schemas.structure import TopicLearningObjects, TopicSpanOutline
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


def _pass2_concurrency() -> int:
    """Thread count for concurrent Pass-2 topic calls (IO-bound LLM HTTP).

    N topics take ~one call's latency instead of N. Clamped 1..10 so a
    huge map cannot blow the provider's per-minute rate window.
    """
    try:
        n = int(get_settings().structure_pass2_concurrency or 4)
    except Exception:
        n = 4
    return max(1, min(10, n))


def _is_rate_limit_error(exc: Exception) -> bool:
    return getattr(getattr(exc, "response", None), "status_code", None) == 429


# Seconds a Pass-2 thread waits out a 429 rate window before its one retry.
# The worker thread (not the Celery worker) blocks — other topics proceed.
_PASS2_429_WAIT_S = 60


def _extract_topic_objects(
    topic_span: TopicSpanOutline,
    source: str,
    *,
    owner_id,
    project_id,
) -> tuple[TopicSpanOutline, TopicLearningObjects | None, bool]:
    """One topic's Pass-2 call, sized for the thread pool. Never raises.

    Returns (topic_span, lo_result | None, failed). References the
    module-global ``extract_learning_objects`` so test patches keep working.
    A 429 waits out one rate window and retries once; anything still
    failing marks the topic failed (skipped downstream, reported).
    """
    if not source.strip():
        return (topic_span, None, True)
    for attempt in (0, 1):
        try:
            with ai_usage_service.track_llm_call(
                user_id=owner_id,
                project_id=project_id,
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
            return (topic_span, lo_result, False)
        except (StructureExtractionError, ValueError, RuntimeError) as e:
            logger.warning("Pass 2 failed for topic %r: %s", topic_span.title, e)
            return (topic_span, None, True)
        except httpx.HTTPError as e:
            if _is_rate_limit_error(e) and attempt == 0:
                logger.warning(
                    "Pass 2 rate-limited for topic %r — waiting out the window",
                    topic_span.title,
                )
                time.sleep(_PASS2_429_WAIT_S)
                continue
            # One topic's transport failure must not fail the whole map.
            logger.warning("Pass 2 transport error for topic %r: %s", topic_span.title, e)
            return (topic_span, None, True)
    logger.warning("Pass 2 still rate-limited for topic %r — skipping", topic_span.title)
    return (topic_span, None, True)


def _attach_stored_figures(db, material: Material, pages: list[dict]) -> None:
    """Append stored figure knowledge to re-read page texts (no vision cost).

    process_pdf already captioned + persisted figures; the structure re-read
    runs with vision off, so re-attach summaries/tables here in place.
    Best-effort — a missing table never breaks the map.
    """
    try:
        from app.models.material_figure import MaterialFigure

        rows = (
            db.query(MaterialFigure)
            .filter(MaterialFigure.material_id == material.id)
            .order_by(MaterialFigure.page_number.asc(), MaterialFigure.fig_index.asc())
            .all()
        )
    except Exception as e:
        logger.warning("figure re-attach skipped: %s", e)
        return
    if not rows:
        return
    by_page: dict[int, list] = {}
    for r in rows:
        by_page.setdefault(r.page_number, []).append(r)
    for page in pages:
        try:
            number = int(page.get("page_number", 0))
        except (TypeError, ValueError):
            continue
        blocks = []
        for r in by_page.get(number, [])[:4]:
            label = f"[Figure p{number}.{r.fig_index} ({str(r.figure_type or 'diagram').lower()})"
            summary = (r.summary or "").strip()
            blocks.append(f"{label}: {summary}]" if summary else f"{label}]")
            if r.figure_type == "CHART" and (r.markdown_table or "").strip():
                blocks.append((r.markdown_table or "").strip()[:4000])
            elif r.figure_type == "TABLE_SCAN" and (r.latex_table or "").strip():
                blocks.append("```latex\n" + (r.latex_table or "").strip()[:4000] + "\n```")
        if blocks:
            page["text"] = ((page.get("text") or "").rstrip() + "\n\n" + "\n".join(blocks)).strip()


def _load_pages(material: Material, db=None) -> tuple[list[dict], int]:
    """Per-page texts for page-tagged extraction (Phase B).

    Prefers the routed pages ``process_pdf`` stashed in Redis (same routing,
    zero re-read — scanned pages are NOT OCR'd twice); falls back to
    re-reading the stored PDF (page boundaries are not kept in
    extracted_text), then to the stored blob as one pseudo-page so
    legacy/odd materials still map instead of failing.

    Vision stays OFF on the re-read path on purpose: process_pdf already
    spent the vision budget and persisted figures — _attach_stored_figures
    re-attaches that knowledge from the DB instead of paying twice.
    """
    try:
        from app.services import pages_cache_service

        cached = pages_cache_service.load_cached_pages(material.id)
        if cached and any((p.get("text") or "").strip() for p in cached):
            if db is not None:
                _attach_stored_figures(db, material, cached)
            return cached, material.page_count or len(cached)
    except Exception as e:
        logger.warning("structure pages cache miss, re-reading: %s", e)
    try:
        pages = extract_pages(material.storage_path, vision_enabled=False)
        numbered = [p for p in pages if (p.get("text") or "").strip()]
        if numbered:
            if db is not None:
                _attach_stored_figures(db, material, pages)
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
    learning objects per topic, concurrently (IO-bound LLM calls); persist
    is one atomic identity-preserving commit. Same lifecycle/backoff contract as before: provider failures fail
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

        pages, page_count = _load_pages(material, db)
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

        # Pass 2 per topic — concurrent (IO-bound LLM calls): N topics take
        # ~one call's latency instead of N. Sources are sliced up-front in
        # the main thread (pure function); only plain values cross into
        # worker threads — the DB session is never shared. Order of
        # topic_results matches topic_map so persistence is deterministic.
        # Individual topic failures skip (reported), the rest of the map
        # still persists. LLM transport errors inside Pass 2 are per-topic:
        # retried once inside the worker on 429s, then skipped.
        project_id = material.project_id
        topic_sources = [
            (topic_span, slice_topic_source(pages, topic_span.page_start, topic_span.page_end))
            for topic_span in topic_map.topics
        ]
        topic_results = []
        failed_topics: list[str] = []
        workers = min(_pass2_concurrency(), len(topic_sources))
        if workers <= 1:
            ordered = [
                _extract_topic_objects(ts, src, owner_id=owner_id, project_id=project_id)
                for ts, src in topic_sources
            ]
        else:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="struct-pass2") as pool:
                ordered = list(
                    pool.map(
                        lambda ts_src: _extract_topic_objects(
                            ts_src[0], ts_src[1], owner_id=owner_id, project_id=project_id
                        ),
                        topic_sources,
                    )
                )
        for topic_span, lo_result, failed in ordered:
            topic_results.append((topic_span, lo_result))
            if failed:
                failed_topics.append(topic_span.title)

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
