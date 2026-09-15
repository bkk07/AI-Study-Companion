import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.schemas.structure import StructureOutline
from app.services.structure_persistence_service import persist_structure


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _client_and_engine():
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
    return TestClient(app), engine


def _register_login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


OUTLINE = {
    "topics": [
        {
            "title": "Algebra",
            "subtopics": [
                {
                    "title": "Linear equations",
                    "concepts": [
                        {"title": "Slope", "summary": "Rise over run."},
                        {"title": "Intercept", "summary": "Crosses axis."},
                    ],
                },
                {
                    "title": "Quadratics",
                    "concepts": [{"title": "Parabola", "summary": "U-shaped curve."}],
                },
            ],
        },
        {
            "title": "Geometry",
            "subtopics": [
                {
                    "title": "Triangles",
                    "concepts": [{"title": "Pythagoras", "summary": "a2 + b2 = c2."}],
                }
            ],
        },
    ]
}


def _setup(client: TestClient, headers: dict) -> str:
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
    sid = resp.json()["id"]
    resp = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers)
    return resp.json()["id"]


def test_structure_tree_empty_then_populated_and_isolated():
    client, engine = _client_and_engine()
    try:
        email_a = f"st_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"st_{uuid.uuid4().hex[:8]}@example.com"
        token_a = _register_login(client, email_a)
        token_b = _register_login(client, email_b)
        h_a = {"Authorization": f"Bearer {token_a}"}
        h_b = {"Authorization": f"Bearer {token_b}"}

        pid_a = _setup(client, h_a)
        pid_b = _setup(client, h_a)

        # empty project returns empty tree
        resp = client.get(f"/api/v1/projects/{pid_a}/structure", headers=h_a)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"topics": []}

        # seed project A directly via persistence service
        Sess = sessionmaker(bind=engine)
        db = Sess()
        persist_structure(db, uuid.UUID(pid_a), StructureOutline.model_validate(OUTLINE))
        db.close()

        # own tree: nested shape, ordered, no leaks
        resp = client.get(f"/api/v1/projects/{pid_a}/structure", headers=h_a)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert [t["title"] for t in body["topics"]] == ["Algebra", "Geometry"]
        algebra = body["topics"][0]
        assert [s["title"] for s in algebra["subtopics"]] == ["Linear equations", "Quadratics"]
        assert [c["title"] for c in algebra["subtopics"][0]["concepts"]] == ["Slope", "Intercept"]
        assert algebra["subtopics"][0]["concepts"][0]["summary"] == "Rise over run."
        raw = resp.text
        assert "storage_path" not in raw
        assert "prompt" not in raw.lower()
        assert "celery" not in raw.lower()

        # project B (same owner, different project) is still empty — no leak
        resp = client.get(f"/api/v1/projects/{pid_b}/structure", headers=h_a)
        assert resp.status_code == 200
        assert resp.json() == {"topics": []}

        # foreign user cannot see A's tree
        resp = client.get(f"/api/v1/projects/{pid_a}/structure", headers=h_b)
        assert resp.status_code in (403, 404), resp.text

        # no token -> 401
        resp = client.get(f"/api/v1/projects/{pid_a}/structure")
        assert resp.status_code == 401

        # nonexistent project -> 404
        resp = client.get(f"/api/v1/projects/{uuid.uuid4()}/structure", headers=h_a)
        assert resp.status_code == 404

        # cleanup
        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email.in_([email_a, email_b])).delete(synchronize_session=False)
        db.commit()
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
