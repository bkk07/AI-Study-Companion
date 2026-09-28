"""Short-lived cache for routed extraction pages (worker only).

``process_pdf`` already routes every page (TEXT/OCR/tables/figures); the
structure worker used to re-open and re-route the whole PDF to recover page
boundaries — paying PyMuPDF + find_tables twice, and Tesseract twice on
scanned docs. Instead the extraction worker stashes the routed pages in
Redis (TTL 1h) and ``build_structure`` reuses them, falling back to the
on-disk re-read whenever the cache misses or looks wrong.

Never raises: Redis down, oversized payload, or odd shape all degrade to
``None``/``False`` and the caller re-reads. Skipped entirely under pytest
so unit tests stay deterministic and broker-free.
"""

import json
import logging
import os
import uuid

log = logging.getLogger(__name__)

_CACHE_TTL_S = 3600
# Routed pages for a 100-page doc are ~1MB; above this, skip caching and
# let the caller re-read rather than pressuring the broker.
_CACHE_MAX_BYTES = 2_000_000


def _cache_key(material_id: uuid.UUID | str) -> str:
    return f"pages:{material_id}"


def _client():
    """Redis client on the Celery broker URL, or None (never raises)."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    try:
        import redis

        from app.core.config import get_settings

        return redis.Redis.from_url(
            get_settings().celery_broker_url,
            socket_connect_timeout=0.5,
            socket_timeout=2.0,
        )
    except Exception as e:
        log.warning("pages cache unavailable: %s", str(e)[:150])
        return None


def cache_extraction_pages(material_id: uuid.UUID | str, pages: list[dict]) -> bool:
    """Stash routed pages for the structure worker. Never raises."""
    if os.getenv("PYTEST_CURRENT_TEST") or not pages:
        return False
    try:
        clean: list[dict] = []
        for p in pages:
            if not isinstance(p, dict):
                continue
            record = {k: v for k, v in p.items() if k != "_png_bytes"}
            clean.append(record)
        payload = json.dumps(clean)
        if len(payload.encode("utf-8")) > _CACHE_MAX_BYTES:
            log.info("pages cache skipped (material=%s, oversized)", material_id)
            return False
        client = _client()
        if client is None:
            return False
        client.setex(_cache_key(material_id), _CACHE_TTL_S, payload)
        return True
    except Exception as e:
        log.warning("pages cache write failed (material=%s): %s", material_id, str(e)[:150])
        return False


def load_cached_pages(material_id: uuid.UUID | str) -> list[dict] | None:
    """Newest routed pages for a material, or None (miss/invalid/down)."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    try:
        client = _client()
        if client is None:
            return None
        raw = client.get(_cache_key(material_id))
        if not raw:
            return None
        pages = json.loads(raw)
        if not isinstance(pages, list) or not pages:
            return None
        for p in pages:
            if not isinstance(p, dict):
                return None
            try:
                int(p.get("page_number", 0))
            except (TypeError, ValueError):
                return None
            if "text" in p and not isinstance(p.get("text"), str):
                return None
        return pages
    except Exception as e:
        log.warning("pages cache read failed (material=%s): %s", material_id, str(e)[:150])
        return None
