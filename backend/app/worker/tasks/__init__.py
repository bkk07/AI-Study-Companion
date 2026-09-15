from app.worker.celery_app import celery_app


@celery_app.task(name="ping", bind=True)
def ping(self) -> str:
    """Trivial task to prove broker→worker→backend wiring (Phase 21)."""
    return "pong"


@celery_app.task(name="add", bind=True)
def add(self, a: int, b: int) -> int:
    """Optional helper for manual verification."""
    return a + b


# Ensure extraction task is registered when tasks package is included
import app.worker.tasks.extraction  # noqa: F401,E402
