from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.practice import PracticeCandidateRead, PracticeRecommendationsRead
from app.services import dashboard_service, recommendation_service
from app.services.mastery_levels import status_for
from app.services.rollup_service import display_mastery
from app.services.mastery_service import mastery_for_concept

router = APIRouter(prefix="/projects/{project_id}/practice", tags=["practice"])


@router.get("/recommendations", response_model=PracticeRecommendationsRead)
def get_recommendations(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=4, ge=1, le=8),
) -> PracticeRecommendationsRead:
    """Recommended-tab ranking: CORE-only top-N practice targets (pure query).

    Nothing is persisted here — the dashboard's single-active recommendation
    contract is untouched. Neutral fallback when nothing has evidence yet.
    """
    _, signals = dashboard_service.build_dashboard(db, user_id=user.id, project_id=project.id)
    try:
        ranked, fallback = recommendation_service.recommend_many(
            db, user_id=user.id, project_id=project.id, signals=signals, limit=limit,
            goal_keywords=recommendation_service.goal_keywords_for_project(project.name),
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    def _card(candidate) -> PracticeCandidateRead:
        scores = mastery_for_concept(
            db, user_id=user.id, project_id=project.id, concept_id=candidate.signal.concept_id
        )
        mastery = display_mastery(scores)
        return PracticeCandidateRead(
            concept_id=candidate.signal.concept_id,
            name=candidate.signal.name,
            lo_type=candidate.signal.lo_type,
            mastery=mastery,
            status=status_for(mastery),
            score=candidate.score,
            reasoning=candidate.reasoning,
            fallback=candidate.fallback,
        )

    items = [_card(c) for c in ranked]
    if not items and fallback is None:
        raise HTTPException(status_code=404, detail="no core learning targets yet")
    return PracticeRecommendationsRead(items=items, fallback=_card(fallback) if fallback else None)
