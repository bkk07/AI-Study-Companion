import uuid
from sqlalchemy.orm import Session

from app.models.space import Space


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    text = description.strip()
    if not text:
        return None
    if len(text) > 2000:
        raise ValueError("Space description must be at most 2000 characters")
    return text


def create_space(db: Session, user_id: uuid.UUID, name: str, description: str | None = None) -> Space:
    name = name.strip()
    if not name:
        raise ValueError("Space name must not be empty")
    if len(name) > 255:
        raise ValueError("Space name must be at most 255 characters")
    space = Space(user_id=user_id, name=name, description=_clean_description(description))
    db.add(space)
    db.commit()
    db.refresh(space)
    return space


def list_spaces(db: Session, user_id: uuid.UUID) -> list[Space]:
    return db.query(Space).filter(Space.user_id == user_id).order_by(Space.created_at.asc()).all()


def get_space(db: Session, space_id: uuid.UUID, user_id: uuid.UUID) -> Space | None:
    return db.query(Space).filter(Space.id == space_id, Space.user_id == user_id).first()
