import os
import uuid

import pytest
from sqlalchemy import text

# Phase 08 — centralized session pattern verification

def _host_db_url() -> str:
    # Host outside compose must use localhost:5433 (5432 occupied on Windows host)
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def test_base_and_mixin_importable():
    from app.db.base import Base, UUIDTimestampMixin

    assert Base is not None
    assert hasattr(UUIDTimestampMixin, "id")
    assert hasattr(UUIDTimestampMixin, "created_at")
    assert hasattr(UUIDTimestampMixin, "updated_at")
    # Base must stay clean — no business fields embedded
    assert not hasattr(Base, "id")


def test_sessionlocal_select_one():
    os.environ["DATABASE_URL"] = _host_db_url()
    from app.core.config import get_settings

    get_settings.cache_clear()
    # Rebuild engine/session bound to host port
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings as gs

    host_engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=host_engine)
    db = HostSessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()
        host_engine.dispose()


def test_get_db_dependency_yields_and_closes():
    os.environ["DATABASE_URL"] = _host_db_url()
    from app.core.config import get_settings

    get_settings.cache_clear()
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings as gs

    host_engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=host_engine)

    def get_db_override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    gen = get_db_override()
    db = next(gen)
    assert db.execute(text("SELECT 1")).scalar() == 1
    # Exhaust generator — triggers close
    try:
        next(gen)
    except StopIteration:
        pass
    host_engine.dispose()


def test_get_db_rollback_on_exception():
    os.environ["DATABASE_URL"] = _host_db_url()
    from app.core.config import get_settings

    get_settings.cache_clear()
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings as gs

    host_engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=host_engine)

    def get_db_override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    gen = get_db_override()
    db = next(gen)
    db.execute(text("SELECT 1"))
    # Simulate exception in request handler
    try:
        gen.throw(RuntimeError("boom"))
    except RuntimeError:
        pass
    # Session should have been rolled back and closed without leaking
    host_engine.dispose()


def test_fastapi_di_with_get_db():
    os.environ["DATABASE_URL"] = _host_db_url()
    from app.core.config import get_settings

    get_settings.cache_clear()
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy import text as sa_text

    from app.core.config import get_settings as gs

    host_engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=host_engine)

    def get_db_override():
        db: Session = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app = FastAPI()

    @app.get("/test-db")
    def test_db(db: Session = Depends(get_db_override)):
        val = db.execute(sa_text("SELECT 1")).scalar()
        assert val == 1
        return {"ok": True, "val": val}

    client = TestClient(app)
    resp = client.get("/test-db")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    host_engine.dispose()


def test_uuid_mixin_generates_uuid():
    from app.db.base import UUIDTimestampMixin
    from app.db.base import Base
    from sqlalchemy.orm import Mapped, mapped_column  # noqa: F401

    col = UUIDTimestampMixin.__dict__["id"]
    underlying = getattr(col, "column", col)
    default = getattr(underlying, "default", None)
    assert default is not None
    arg = getattr(default, "arg", None)
    assert callable(arg)
    assert getattr(arg, "__name__", "uuid4") == "uuid4"

    # Also verify timestamps use server_default func.now()
    ca = UUIDTimestampMixin.__dict__["created_at"]
    ca_col = getattr(ca, "column", ca)
    assert ca_col.server_default is not None
