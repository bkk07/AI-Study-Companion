import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.growth import (
    ConceptCurrentRead,
    ConceptGrowthRead,
    GrowthPointRead,
    ProjectGrowthRead,
)
from app.services import growth_service

router = APIRouter(prefix="/projects/{project_id}/growth", tags=["growth"])


@router.get("", response_model=ProjectGrowthRead | ConceptGrowthRead)
def get_growth(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    concept_id: uuid.UUID | None = Query(default=None),
) -> ProjectGrowthRead | ConceptGrowthRead:
    """Project overview, or one concept's running-mastery series. Reads only."""
    try:
        if concept_id is not None:
            growth = growth_service.concept_growth(
                db, user_id=user.id, project_id=project.id, concept_id=concept_id
            )
            return ConceptGrowthRead(
                concept_id=growth.concept_id,
                points=[
                    GrowthPointRead(at=p.at, evidence_type=p.evidence_type, raw_score=p.raw_score,
                                    mcq_after=p.mcq_after, applied_after=p.applied_after)
                    for p in growth.points
                ],
                mcq_trend=growth.mcq_trend,
                applied_trend=growth.applied_trend,
                count=growth.count,
            )
        overview = growth_service.project_growth(db, user_id=user.id, project_id=project.id)
        return ProjectGrowthRead(
            concepts=[
                ConceptCurrentRead(concept_id=c.concept_id, title=c.title, mcq=c.mcq,
                                   applied=c.applied, count=c.count)
                for c in overview.concepts
            ],
            avg_mcq=overview.avg_mcq,
            avg_applied=overview.avg_applied,
            evidenced_concepts=overview.evidenced_concepts,
            total_evidence=overview.total_evidence,
            since=overview.since,
            until=overview.until,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
