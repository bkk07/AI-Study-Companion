import os
import uuid

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
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _cleanup_user(client: TestClient, email: str, engine):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()


def test_projects_nested_create_and_list():
    client, engine, _ = _override_and_client()
    try:
        email = f"proj_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        # create space
        resp = client.post("/api/v1/spaces", json={"name": "MySpace"}, headers=headers)
        assert resp.status_code == 201, resp.text
        space_id = resp.json()["id"]

        # create project
        resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "ProjA"}, headers=headers)
        assert resp.status_code == 201, resp.text
        proj = resp.json()
        assert proj["name"] == "ProjA"
        assert proj["space_id"] == space_id

        resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": "ProjB"}, headers=headers)
        assert resp.status_code == 201

        # list
        resp = client.get(f"/api/v1/spaces/{space_id}/projects", headers=headers)
        assert resp.status_code == 200, resp.text
        names = {p["name"] for p in resp.json()}
        assert names == {"ProjA", "ProjB"}

        _cleanup_user(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_projects_isolation_foreign_space():
    client, engine, _ = _override_and_client()
    try:
        email_a = f"a_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"b_{uuid.uuid4().hex[:8]}@example.com"
        token_a = _register_and_login(client, email_a)
        token_b = _register_and_login(client, email_b)
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # A creates space + project
        resp = client.post("/api/v1/spaces", json={"name": "ASpace"}, headers=headers_a)
        space_a = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_a}/projects", json={"name": "AProj"}, headers=headers_a)
        assert resp.status_code == 201

        # B tries to list A's space projects -> 404
        resp = client.get(f"/api/v1/spaces/{space_a}/projects", headers=headers_b)
        assert resp.status_code == 404

        # B tries to create in A's space -> 404
        resp = client.post(f"/api/v1/spaces/{space_a}/projects", json={"name": "BProj"}, headers=headers_b)
        assert resp.status_code == 404

        # B creates own space, sees isolation
        resp = client.post("/api/v1/spaces", json={"name": "BSpace"}, headers=headers_b)
        space_b = resp.json()["id"]
        resp = client.get(f"/api/v1/spaces/{space_b}/projects", headers=headers_b)
        assert resp.json() == []

        _cleanup_user(client, email_a, engine)
        _cleanup_user(client, email_b, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_projects_require_auth_and_validation():
    client, engine, _ = _override_and_client()
    try:
        # no auth
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/api/v1/spaces/{fake_id}/projects", json={"name": "X"})
        assert resp.status_code == 401
        resp = client.get(f"/api/v1/spaces/{fake_id}/projects")
        assert resp.status_code == 401

        # auth but invalid space_id -> 404
        email = f"val_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/v1/spaces/{fake_id}/projects", json={"name": "X"}, headers=headers)
        assert resp.status_code == 404

        # empty name -> 400/422
        resp = client.post("/api/v1/spaces", json={"name": "Tmp"}, headers=headers)
        space_id = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_id}/projects", json={"name": ""}, headers=headers)
        assert resp.status_code in (400, 422)

        _cleanup_user(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
