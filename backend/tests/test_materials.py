import os
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models.material import Material
from app.models.project import Project
from app.models.space import Space
from app.models.user import User
from app.core.security import hash_password


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _engine():
    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    return create_engine(gs().database_url, pool_pre_ping=True, future=True)


def test_material_round_trips():
    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        # setup user/space/project
        email = f"mat_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=email, hashed_password=hash_password("supersecret123"))
        db.add(user)
        db.commit()
        db.refresh(user)

        space = Space(user_id=user.id, name="MatSpace")
        db.add(space)
        db.commit()
        db.refresh(space)

        project = Project(space_id=space.id, name="MatProject")
        db.add(project)
        db.commit()
        db.refresh(project)

        # create material
        mat = Material(project_id=project.id, filename="doc.pdf", storage_path="/data/uploads/doc.pdf", status="pending")
        db.add(mat)
        db.commit()
        db.refresh(mat)

        # verify read
        fetched = db.query(Material).filter(Material.id == mat.id).first()
        assert fetched is not None
        assert fetched.filename == "doc.pdf"
        assert fetched.storage_path == "/data/uploads/doc.pdf"
        assert fetched.status == "pending"
        assert fetched.project_id == project.id
        assert fetched.created_at is not None

        # server_default: insert without status → pending
        mat2 = Material(project_id=project.id, filename="doc2.pdf", storage_path="/data/uploads/doc2.pdf", status="pending")
        # also test default via raw insert without status
        db.execute(
            text("INSERT INTO materials (id, project_id, filename, storage_path, created_at, updated_at) VALUES (:id, :pid, :fn, :sp, now(), now())"),
            {"id": str(uuid.uuid4()), "pid": str(project.id), "fn": "raw.pdf", "sp": "/data/uploads/raw.pdf"},
        )
        db.commit()
        raw = db.query(Material).filter(Material.filename == "raw.pdf").first()
        assert raw is not None
        assert raw.status == "pending"

        # FK cascade: deleting project cascades materials? cleanup via user delete
        db.query(Material).filter(Material.project_id == project.id).delete()
        db.commit()
        assert db.query(Material).filter(Material.project_id == project.id).count() == 0

        # cleanup
        db.query(Project).filter(Project.id == project.id).delete()
        db.query(Space).filter(Space.id == space.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
    finally:
        db.close()
        engine.dispose()


def test_material_schema_read():
    # Pydantic read without storage leak? just ensure from_attributes works
    from app.schemas.material import MaterialRead

    data = {
        "id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "filename": "a.pdf",
        "storage_path": "/data/uploads/a.pdf",
        "status": "pending",
        "created_at": "2026-09-15T00:00:00Z",
        "updated_at": "2026-09-15T00:00:00Z",
    }
    m = MaterialRead.model_validate({**data, "created_at": "2026-09-15T00:00:00+00:00", "updated_at": "2026-09-15T00:00:00+00:00"})
    assert m.filename == "a.pdf"
    assert m.status == "pending"
