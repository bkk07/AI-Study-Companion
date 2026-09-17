from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverviewRead,
    BeforeNowRead,
    ConfidencePointRead,
    ProjectAnalyticsRead,
    TimelinePointRead,
    TopicMasteryRead,
)
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
        core_concepts_count=stats.core_concepts_count,
        quiz_attempts=stats.quiz_attempts,
        quiz_attempts_completed=stats.quiz_attempts_completed,
        avg_mcq=stats.avg_mcq,
        avg_applied=stats.avg_applied,
        avg_final=stats.avg_final,
        evidenced_concepts=stats.evidenced_concepts,
        tutor_interactions=stats.tutor_interactions,
    )


@router.get("/overview", response_model=AnalyticsOverviewRead)
def get_analytics_overview(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    time_range: str = Query(default="all", pattern="^(2w|1m|all)$"),
) -> AnalyticsOverviewRead:
    """Figma Analytics page read-model: counts, topic mastery, confidence
    scatter, mastery timeline, and before-vs-now. Read-only."""
    try:
        overview = analytics_service.analytics_overview(
            db, user_id=user.id, project_id=project.id, time_range=time_range
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AnalyticsOverviewRead(
        materials_total=overview.materials_total,
        concepts_count=overview.concepts_count,
        core_concepts_count=overview.core_concepts_count,
        topics_count=overview.topics_count,
        quiz_attempts=overview.quiz_attempts,
        quiz_attempts_completed=overview.quiz_attempts_completed,
        flashcards_total=overview.flashcards_total,
        tutor_interactions=overview.tutor_interactions,
        assessments_total=overview.assessments_total,
        avg_mcq=overview.avg_mcq,
        avg_applied=overview.avg_applied,
        evidenced_concepts=overview.evidenced_concepts,
        streak_days=overview.streak_days,
        topic_mastery=[
            TopicMasteryRead(topic=t.topic, mcq=t.mcq, applied=t.applied)
            for t in overview.topic_mastery
        ],
        confidence_points=[
            ConfidencePointRead(
                concept_id=str(c.concept_id),
                concept=c.concept,
                confidence=c.confidence,
                correctness=c.correctness,
                attempts=c.attempts,
                mismatch_type=c.mismatch_type,
            )
            for c in overview.confidence_points
        ],
        timeline=[
            TimelinePointRead(date=t.date, label=t.label, mcq=t.mcq, applied=t.applied)
            for t in overview.timeline
        ],
        before_now=[
            BeforeNowRead(
                concept_id=str(b.concept_id),
                concept=b.concept,
                early_mcq=b.early_mcq,
                early_applied=b.early_applied,
                current_mcq=b.current_mcq,
                current_applied=b.current_applied,
            )
            for b in overview.before_now
        ],
    )
