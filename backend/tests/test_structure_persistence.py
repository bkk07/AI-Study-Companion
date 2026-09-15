import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.subtopic import Subtopic
from app.models.topic import Topic
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


def _make_project(client: TestClient, headers: dict) -> str:
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
    sid = resp.json()["id"]
    resp = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=headers)
    return resp.json()["id"]


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
                }
            ],
        }
    ]
}


def test_persist_and_idempotent_rerun():
    client, engine = _client_and_engine()
    try:
        email = f"sp_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_login(client, email)
        h = {"Authorization": f"Bearer {token}"}
        pid = _make_project(client, h)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        outline = StructureOutline.model_validate(OUTLINE)
        counts1 = persist_structure(db, uuid.UUID(pid), outline)
        assert counts1 == {"topics": 1, "subtopics": 1, "concepts": 2}
        ids1 = (
            [t.id for t in db.query(Topic).filter(Topic.project_id == uuid.UUID(pid)).all()],
            [s.id for s in db.query(Subtopic).filter(Subtopic.project_id == uuid.UUID(pid)).all()],
            sorted(c.id for c in db.query(Concept).filter(Concept.project_id == uuid.UUID(pid)).all()),
        )
        # identical re-run: same ids, same counts, no duplicates
        counts2 = persist_structure(db, uuid.UUID(pid), outline)
        assert counts2 == counts1
        ids2 = (
            [t.id for t in db.query(Topic).filter(Topic.project_id == uuid.UUID(pid)).all()],
            [s.id for s in db.query(Subtopic).filter(Subtopic.project_id == uuid.UUID(pid)).all()],
            sorted(c.id for c in db.query(Concept).filter(Concept.project_id == uuid.UUID(pid)).all()),
        )
        assert ids1 == ids2
        # case/whitespace variant matches same rows, updates casing
        variant = StructureOutline.model_validate(
            {"topics": [{"title": "  algebra ", "subtopics": [{"title": "LINEAR EQUATIONS", "concepts": [{"title": " slope ", "summary": "Rise over run."}, {"title": "Intercept", "summary": "Crosses axis."}]}]}]}
        )
        counts3 = persist_structure(db, uuid.UUID(pid), variant)
        assert counts3 == counts1
        assert db.query(Topic).filter(Topic.project_id == uuid.UUID(pid)).count() == 1
        db.close()

        # cleanup
        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()


def test_summary_update_in_place_and_project_isolation():
    client, engine = _client_and_engine()
    try:
        email = f"sp2_{uuid.uuid4().hex[:8]}@example.com"
        token = _register_login(client, email)
        h = {"Authorization": f"Bearer {token}"}
        pid_a = _make_project(client, h)
        pid_b = _make_project(client, h)

        Sess = sessionmaker(bind=engine)
        db = Sess()
        persist_structure(db, uuid.UUID(pid_a), StructureOutline.model_validate(OUTLINE))
        # changed summary updates same concept row
        updated = StructureOutline.model_validate(
            {"topics": [{"title": "Algebra", "subtopics": [{"title": "Linear equations", "concepts": [{"title": "Slope", "summary": "Updated summary."}, {"title": "Intercept", "summary": "Crosses axis."}]}]}]}
        )
        persist_structure(db, uuid.UUID(pid_a), updated)
        slope = db.query(Concept).filter(Concept.project_id == uuid.UUID(pid_a), Concept.title == "Slope").one()
        assert slope.summary == "Updated summary."
        assert db.query(Concept).filter(Concept.project_id == uuid.UUID(pid_a)).count() == 2

        # same titles in another project create separate rows
        persist_structure(db, uuid.UUID(pid_b), StructureOutline.model_validate(OUTLINE))
        assert db.query(Topic).filter(Topic.project_id == uuid.UUID(pid_b)).count() == 1
        assert db.query(Concept).filter(Concept.project_id == uuid.UUID(pid_b)).count() == 2
        db.close()

        db = Sess()
        from app.models.user import User

        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
