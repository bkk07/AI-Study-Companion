import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _get_host_sessionmaker():
    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine), engine


def test_user_model_roundtrip():
    SessionLocal, engine = _get_host_sessionmaker()
    from app.models.user import User

    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    # dummy hash — Phase 11 will add Argon2id, for now any string suffices
    hashed = "$argon2id$v=19$m=65536,t=3,p=4$dummy"

    db = SessionLocal()
    try:
        user = User(email=email, hashed_password=hashed, is_admin=False)
        db.add(user)
        db.commit()
        db.refresh(user)

        assert isinstance(user.id, uuid.UUID)
        assert user.email == email
        assert user.hashed_password == hashed
        assert user.is_admin is False
        assert user.created_at is not None
        assert user.updated_at is not None

        # Read back via query
        fetched = db.query(User).filter(User.email == email).first()
        assert fetched is not None
        assert fetched.id == user.id

        # Pydantic schemas — password not in read
        from app.schemas.user import UserCreate, UserRead

        # UserCreate validates
        uc = UserCreate(email=email, password="supersecret123")
        assert uc.email == email

        # UserRead from_attributes — must not expose hashed_password
        ur = UserRead.model_validate(fetched)
        assert ur.email == email
        assert ur.id == user.id
        assert ur.is_admin is False
        assert ur.created_at is not None
        assert not hasattr(ur, "hashed_password")
        assert "hashed_password" not in ur.model_dump()
        # ensure password field not leaked
        assert not hasattr(ur, "password")

        # cleanup
        db.delete(fetched)
        db.commit()
    finally:
        db.close()
        engine.dispose()


def test_user_email_unique_constraint():
    SessionLocal, engine = _get_host_sessionmaker()
    from sqlalchemy.exc import IntegrityError

    from app.models.user import User

    email = f"uniq_{uuid.uuid4().hex[:8]}@example.com"
    hashed = "$argon2id$dummy"

    db = SessionLocal()
    try:
        u1 = User(email=email, hashed_password=hashed)
        db.add(u1)
        db.commit()

        u2 = User(email=email, hashed_password=hashed)
        db.add(u2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # cleanup
        db.query(User).filter(User.email == email).delete()
        db.commit()
    finally:
        db.close()
        engine.dispose()


def test_user_schema_validation():
    from app.schemas.user import UserCreate

    # valid
    UserCreate(email="a@b.co", password="12345678")
    # invalid email
    with pytest.raises(Exception):
        UserCreate(email="not-an-email", password="12345678")
    # short password
    with pytest.raises(Exception):
        UserCreate(email="a@b.co", password="short")
