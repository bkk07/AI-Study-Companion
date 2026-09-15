import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _override_and_client():
    os.environ["DATABASE_URL"] = _host_url()
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
    client = TestClient(app)
    return client, engine, HostSessionLocal


def _register_and_login(client: TestClient, email: str, pwd: str = "supersecret123") -> str:
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    if resp.status_code == 400:  # already exists from previous run — login instead
        pass
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _cleanup_user(client: TestClient, email: str, engine):
    # delete user cascades spaces
    Sess = sessionmaker(bind=engine)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()


def test_spaces_require_auth():
    client, engine, _ = _override_and_client()
    try:
        resp = client.get("/api/v1/spaces")
        assert resp.status_code == 401
        resp = client.post("/api/v1/spaces", json={"name": "My Space"})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_create_and_list_own_spaces():
    client, engine, _ = _override_and_client()
    try:
        email = f"space_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        # create
        resp = client.post("/api/v1/spaces", json={"name": "Alpha"}, headers=headers)
        assert resp.status_code == 201, resp.text
        space = resp.json()
        assert space["name"] == "Alpha"
        assert "id" in space
        assert "user_id" in space

        resp = client.post("/api/v1/spaces", json={"name": "Beta"}, headers=headers)
        assert resp.status_code == 201

        # list
        resp = client.get("/api/v1/spaces", headers=headers)
        assert resp.status_code == 200, resp.text
        names = {s["name"] for s in resp.json()}
        assert names == {"Alpha", "Beta"}

        _cleanup_user(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_spaces_isolation_between_users():
    client, engine, _ = _override_and_client()
    try:
        email_a = f"a_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"b_{uuid.uuid4().hex[:8]}@example.com"
        token_a = _register_and_login(client, email_a)
        token_b = _register_and_login(client, email_b)
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # A creates one
        resp = client.post("/api/v1/spaces", json={"name": "A Space"}, headers=headers_a)
        assert resp.status_code == 201

        # B should see 0
        resp = client.get("/api/v1/spaces", headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []

        # A sees 1
        resp = client.get("/api/v1/spaces", headers=headers_a)
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "A Space"

        # B creates one, A still 1
        resp = client.post("/api/v1/spaces", json={"name": "B Space"}, headers=headers_b)
        assert resp.status_code == 201
        resp = client.get("/api/v1/spaces", headers=headers_a)
        assert len(resp.json()) == 1
        resp = client.get("/api/v1/spaces", headers=headers_b)
        assert len(resp.json()) == 1

        _cleanup_user(client, email_a, engine)
        _cleanup_user(client, email_b, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_create_space_validation():
    client, engine, _ = _override_and_client()
    try:
        email = f"val_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}
        # empty name should be 422 from pydantic or 400 from service
        resp = client.post("/api/v1/spaces", json={"name": ""}, headers=headers)
        assert resp.status_code in (400, 422)
        # missing name
        resp = client.post("/api/v1/spaces", json={}, headers=headers)
        assert resp.status_code == 422

        _cleanup_user(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
