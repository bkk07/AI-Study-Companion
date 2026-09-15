import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead
from app.services import project_service

router = APIRouter(prefix="/spaces/{space_id}/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    space_id: uuid.UUID,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = project_service.create_project(db, current_user.id, space_id, payload.name)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    space_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = project_service.list_projects(db, current_user.id, space_id)
    return projects
