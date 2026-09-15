import uuid
from sqlalchemy.orm import Session

from app.models.space import Space


def create_space(db: Session, user_id: uuid.UUID, name: str) -> Space:
    name = name.strip()
    if not name:
        raise ValueError("Space name must not be empty")
    space = Space(user_id=user_id, name=name)
    db.add(space)
    db.commit()
    db.refresh(space)
    return space


def list_spaces(db: Session, user_id: uuid.UUID) -> list[Space]:
    return db.query(Space).filter(Space.user_id == user_id).order_by(Space.created_at.asc()).all()


def get_space(db: Session, space_id: uuid.UUID, user_id: uuid.UUID) -> Space | None:
    return db.query(Space).filter(Space.id == space_id, Space.user_id == user_id).first()
