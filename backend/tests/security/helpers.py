"""Shared fixtures for Phase 49 security tests (real PG, real app wiring)."""

import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.rate_limit import reset_budgets
from app.db.session import get_db
from app.main import app


def setup(tmpdir: str | None = None):
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    if tmpdir:
        os.environ["UPLOAD_DIR"] = tmpdir
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def teardown(engine):
    app.dependency_overrides.clear()
    reset_budgets()
    engine.dispose()
    get_settings.cache_clear()
    os.environ.pop("UPLOAD_DIR", None)


def login(client: TestClient, email: str) -> dict:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def make_project(client: TestClient, headers: dict, suffix: str = "S") -> tuple[str, str]:
    resp = client.post("/api/v1/spaces", json={"name": f"Sec{suffix}"}, headers=headers)
    assert resp.status_code == 201, resp.text
    space_id = resp.json()["id"]
    resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": f"SecP{suffix}"}, headers=headers)
    assert resp.status_code == 201, resp.text
    return space_id, resp.json()["id"]


def tag(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"
