from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_engine() -> Engine:
    """
    Build SQLAlchemy engine from DATABASE_URL (env).
    Single relational engine — no second DB.
    Pool pre-ping keeps the check honest against idle connections.
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


# Singleton engine
engine: Engine = get_engine()

# Centralized session factory — Phase 08
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields a Session and ensures close/rollback.
    All relational access must use this pattern (Phase 08 guard).
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
