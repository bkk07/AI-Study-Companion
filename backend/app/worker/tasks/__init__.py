from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.worker.celery_app import celery_app


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
import app.worker.tasks.structure  # noqa: F401,E402
