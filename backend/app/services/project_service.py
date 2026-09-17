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


def _clean_optional(text: str | None, *, field: str, limit: int) -> str | None:
    if text is None:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project {field} must be at most {limit} characters",
        )
    return cleaned


def create_project(
    db: Session,
    user_id: uuid.UUID,
    space_id: uuid.UUID,
    name: str,
    description: str | None = None,
    goal: str | None = None,
) -> Project:
    _get_owned_space(db, space_id, user_id)
    name = name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name must not be empty")
    if len(name) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name must be at most 255 characters")
    project = Project(
        space_id=space_id,
        name=name,
        description=_clean_optional(description, field="description", limit=2000),
        goal=_clean_optional(goal, field="goal", limit=1000),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    # §12: project.created — idempotent on retry.
    from app.services import activity_service

    activity_service.record_event_committed(
        db,
        user_id=user_id,
        project_id=project.id,
        space_id=space_id,
        event_type=activity_service.EVENT_PROJECT_CREATED,
        entity_type="project",
        entity_id=project.id,
        payload={},
        idempotency_key=f"project:{project.id}:created",
    )
    return project


def list_projects(db: Session, user_id: uuid.UUID, space_id: uuid.UUID) -> list[Project]:
    _get_owned_space(db, space_id, user_id)
    return db.query(Project).filter(Project.space_id == space_id).order_by(Project.created_at.asc()).all()
