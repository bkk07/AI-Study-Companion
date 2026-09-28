from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_study_companion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks", "app.worker.tasks.extraction", "app.worker.tasks.embeddings", "app.worker.tasks.structure", "app.worker.tasks.recommendations"],
)

# Keep serialization simple and keep same env in api/worker
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    # Queue split: CPU-bound extraction/embeddings must never wait behind
    # network-bound structure builds (and vice versa). Dispatch sites keep
    # using .delay() — routing happens here, so tests and callers are
    # unaffected. `generate_recommendation` is deterministic CPU/DB work, so
    # it stays on the default queue consumed by the CPU worker.
    task_default_queue="celery",
    task_routes={
        "process_pdf": {"queue": "extract"},
        "generate_embeddings": {"queue": "embed"},
        "build_structure": {"queue": "structure"},
    },
)
