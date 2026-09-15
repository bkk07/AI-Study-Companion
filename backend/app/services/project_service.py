import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.space import Space


def _get_owned_space(db: Session, space_id: uuid.UUID, user_id: uuid.UUID) -> Space:
    space = db.query(Space).filter(Space.id == space_id, Space.user_id == user_id).first()
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    return space


def create_project(db: Session, user_id: uuid.UUID, space_id: uuid.UUID, name: str) -> Project:
    _get_owned_space(db, space_id, user_id)
    name = name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name must not be empty")
    if len(name) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name must be at most 255 characters")
    project = Project(space_id=space_id, name=name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, user_id: uuid.UUID, space_id: uuid.UUID) -> list[Project]:
    _get_owned_space(db, space_id, user_id)
    return db.query(Project).filter(Project.space_id == space_id).order_by(Project.created_at.asc()).all()
