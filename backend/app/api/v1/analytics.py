from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.analytics import ProjectAnalyticsRead
from app.services import analytics_service

router = APIRouter(prefix="/projects/{project_id}/analytics", tags=["analytics"])


@router.get("", response_model=ProjectAnalyticsRead)
def get_analytics(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectAnalyticsRead:
    """Aggregate stats for one project. Read-only read-model."""
    try:
        stats = analytics_service.project_analytics(db, user_id=user.id, project_id=project.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ProjectAnalyticsRead(
        materials_total=stats.materials_total,
        materials_by_status=stats.materials_by_status,
        topics_count=stats.topics_count,
        concepts_count=stats.concepts_count,
        quiz_attempts=stats.quiz_attempts,
        quiz_attempts_completed=stats.quiz_attempts_completed,
        avg_mcq=stats.avg_mcq,
        avg_applied=stats.avg_applied,
        evidenced_concepts=stats.evidenced_concepts,
        tutor_interactions=None,
    )
