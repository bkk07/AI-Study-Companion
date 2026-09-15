from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings


def get_engine() -> Engine:
    """
    Build SQLAlchemy engine from DATABASE_URL (env).
    Single relational engine — no second DB. Used for Phase 06 SELECT 1 check.
    Pool pre-ping keeps the check honest against idle connections.
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


# Singleton for convenience; Phase 08 will introduce SessionLocal/get_db()
engine: Engine = get_engine()


def check_db_connection() -> bool:
    """
    Run a real connection check: SELECT 1.
    Returns True if the containerized Postgres is reachable via the configured URL.
    Raises on failure so the verification can surface the error.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        row = result.scalar()
        return row == 1
