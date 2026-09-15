import os
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.jwt import create_access_token
from app.db.session import get_db
from app.main import app


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _get_host_session_override():
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

    return override, engine


@pytest.fixture()
def client_and_engine():
    override, engine = _get_host_session_override()
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


def test_register_and_login_success(client_and_engine):
    client, _ = client_and_engine
    email = f"auth_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "supersecret123"

    # register
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == email
    assert "id" in data
    assert "hashed_password" not in data

    # login
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    assert token.startswith("eyJ")

    # me
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email

    # cleanup — delete user via direct DB
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker as sm

    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs2

    eng = ce(gs2().database_url)
    Sess = sm(bind=eng)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()
    eng.dispose()


def test_register_duplicate_rejected(client_and_engine):
    client, _ = client_and_engine
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "supersecret123"
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    assert resp.status_code == 201
    resp2 = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    assert resp2.status_code == 400

    # cleanup
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker as sm

    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs2

    eng = ce(gs2().database_url)
    Sess = sm(bind=eng)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()
    eng.dispose()


def test_login_invalid_credentials_rejected(client_and_engine):
    client, _ = client_and_engine
    email = f"invalid_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "supersecret123"
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    # wrong pwd
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpass123"})
    assert resp.status_code == 401
    # non-existent email
    resp = client.post("/api/v1/auth/login", json={"email": "nope@example.com", "password": pwd})
    assert resp.status_code == 401

    # cleanup
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker as sm

    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs2

    eng = ce(gs2().database_url)
    Sess = sm(bind=eng)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()
    eng.dispose()


def test_protected_rejects_missing_and_invalid_token(client_and_engine):
    client, _ = client_and_engine
    # missing
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    # malformed
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert resp.status_code == 401
    # wrong scheme
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Token abc"})
    assert resp.status_code == 401


def test_expired_jwt_rejected(client_and_engine):
    client, _ = client_and_engine
    email = f"exp_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "supersecret123"
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    uid = resp.json()["id"]
    # create expired token directly
    expired_token = create_access_token(subject=uid, expires_delta=timedelta(seconds=-1))
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower() or "could not validate" in resp.json()["detail"].lower()

    # cleanup
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker as sm

    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs2

    eng = ce(gs2().database_url)
    Sess = sm(bind=eng)
    db = Sess()
    from app.models.user import User

    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()
    eng.dispose()
