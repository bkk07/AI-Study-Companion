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
    return client, engine


def _register_and_login(client: TestClient, email: str, pwd: str = "supersecret123") -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _cleanup(client: TestClient, email: str, engine):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()


def test_authorization_own_vs_foreign():
    client, engine = _override_and_client()
    try:
        email_a = f"authA_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"authB_{uuid.uuid4().hex[:8]}@example.com"
        token_a = _register_and_login(client, email_a)
        token_b = _register_and_login(client, email_b)
        h_a = {"Authorization": f"Bearer {token_a}"}
        h_b = {"Authorization": f"Bearer {token_b}"}

        # A creates space + project
        resp = client.post("/api/v1/spaces", json={"name": "ASpace"}, headers=h_a)
        assert resp.status_code == 201, resp.text
        space_a = resp.json()["id"]
        resp = client.post(f"/api/v1/spaces/{space_a}/projects", json={"name": "AProj"}, headers=h_a)
        assert resp.status_code == 201, resp.text
        proj_a = resp.json()["id"]

        # own access succeeds
        resp = client.get(f"/api/v1/spaces/{space_a}", headers=h_a)
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == space_a

        resp = client.get(f"/api/v1/projects/{proj_a}", headers=h_a)
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == proj_a

        resp = client.get(f"/api/v1/spaces/{space_a}/projects/{proj_a}", headers=h_a)
        assert resp.status_code == 200, resp.text

        # foreign space -> 403/404
        resp = client.get(f"/api/v1/spaces/{space_a}", headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        resp = client.get(f"/api/v1/projects/{proj_a}", headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        resp = client.get(f"/api/v1/spaces/{space_a}/projects/{proj_a}", headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        # foreign list/create via space also 404
        resp = client.get(f"/api/v1/spaces/{space_a}/projects", headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        resp = client.post(f"/api/v1/spaces/{space_a}/projects", json={"name": "X"}, headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        # B's own isolation: B cannot see A's, but can create own
        resp = client.post("/api/v1/spaces", json={"name": "BSpace"}, headers=h_b)
        space_b = resp.json()["id"]
        resp = client.get(f"/api/v1/spaces/{space_b}", headers=h_b)
        assert resp.status_code == 200

        _cleanup(client, email_a, engine)
        _cleanup(client, email_b, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_authorization_requires_auth():
    client, engine = _override_and_client()
    try:
        fake = str(uuid.uuid4())
        # missing token -> 401
        resp = client.get(f"/api/v1/spaces/{fake}")
        assert resp.status_code == 401
        resp = client.get(f"/api/v1/projects/{fake}")
        assert resp.status_code == 401
        resp = client.get(f"/api/v1/spaces/{fake}/projects/{fake}")
        assert resp.status_code == 401

        # invalid token -> 401
        resp = client.get(f"/api/v1/spaces/{fake}", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401

        # valid token but non-existent resource -> 404 (not 200)
        email = f"authC_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_and_login(client, email)
        h = {"Authorization": f"Bearer {token}"}
        resp = client.get(f"/api/v1/spaces/{fake}", headers=h)
        assert resp.status_code == 404
        resp = client.get(f"/api/v1/projects/{fake}", headers=h)
        assert resp.status_code == 404

        _cleanup(client, email, engine)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
