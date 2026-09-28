from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from celery.signals import worker_process_init

import logging
import os

from app.core.config import get_settings
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)


def get_task_session() -> Session:
    """Fresh DB session from current settings — respects DATABASE_URL override (host localhost vs container postgres)."""
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


@celery_app.task(name="ping", bind=True)
def ping(self) -> str:
    """Trivial task to prove broker→worker→backend wiring (Phase 21)."""
    return "pong"


@celery_app.task(name="add", bind=True)
def add(self, a: int, b: int) -> int:
    """Optional helper for manual verification."""
    return a + b


# Ensure worker tasks are registered when tasks package is included
import app.worker.tasks.embeddings  # noqa: F401,E402
import app.worker.tasks.extraction  # noqa: F401,E402
import app.worker.tasks.recommendations  # noqa: F401,E402
import app.worker.tasks.structure  # noqa: F401,E402


@worker_process_init.connect
def _warm_embedding_model(**kwargs) -> None:
    """Preload the local embedding model in each worker child at startup.

    The model bytes are baked into the image, but the first `embed()` still
    pays ONNX session init (~seconds) — without warmup that stalls the
    first upload's embeddings job. Gated by WARMUP_EMBEDDINGS (CPU worker
    only — the LLM worker never embeds). Fires per forked child, so every
    child is warm. Never raises: a miss just means lazy init later.
    """
    if os.getenv("WARMUP_EMBEDDINGS", "false").lower() not in ("1", "true", "yes"):
        return
    try:
        import time

        from app.services.ai.embedding_client import _local_model

        start = time.perf_counter()
        _local_model()
        log.info("embeddings model warmed in %.1fs", time.perf_counter() - start)
    except Exception as e:
        log.warning("embeddings warmup skipped: %s", str(e)[:200])
