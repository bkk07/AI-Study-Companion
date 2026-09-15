import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.project import Project
from app.models.space import Space
from app.models.user import User


def get_authorized_space(
    space_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Space:
    """Reusable ownership check: user → space. 404 hides existence."""
    space = db.query(Space).filter(Space.id == space_id, Space.user_id == current_user.id).first()
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    return space


def get_authorized_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """Reusable ownership check: user → space → project via join."""
    project = (
        db.query(Project)
        .join(Space, Project.space_id == Space.id)
        .filter(Project.id == project_id, Space.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_authorized_project_in_space(
    space_id: uuid.UUID,
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """Verify both space ownership and project belongs to that space."""
    space = db.query(Space).filter(Space.id == space_id, Space.user_id == current_user.id).first()
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    project = db.query(Project).filter(Project.id == project_id, Project.space_id == space_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
