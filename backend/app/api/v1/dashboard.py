import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.concept import Concept
from app.models.project import Project
from app.models.user import User
from app.schemas.dashboard import (
    ConceptProgressRead,
    DashboardResponse,
    MismatchRead,
    RecommendationRead,
)
from app.services import dashboard_service, recommendation_service
from app.services.mastery_levels import status_for
from app.services.rollup_service import display_mastery

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


def _concept_names(db: Session, concept_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not concept_ids:
        return {}
    return dict(
        db.query(Concept.id, Concept.title).filter(Concept.id.in_(concept_ids)).all()
    )


def _to_response(
    db: Session,
    progress: list[dashboard_service.ConceptProgress],
    recommendation,
) -> DashboardResponse:
    names = _concept_names(db, ({recommendation.concept_id} if recommendation else set()))
    return DashboardResponse(
        concepts=[
            ConceptProgressRead(
                concept_id=p.concept_id,
                title=p.title,
                topic=p.topic,
                subtopic=p.subtopic,
                mcq=p.scores.mcq.value,
                applied=p.scores.applied.value,
                mcq_count=p.scores.mcq.count,
                applied_count=p.scores.applied.count,
                last_evidence_at=max(
                    [s.last_at for s in (p.scores.mcq, p.scores.applied) if s.last_at is not None],
                    default=None,
                ),
                status=status_for(display_mastery(p.scores)),
                avg_confidence=p.avg_confidence,
                accuracy=p.accuracy,
                evaluated_count=p.evaluated_count,
                mismatch=(
                    MismatchRead(mismatch_type=p.mismatch.mismatch_type, gap=p.mismatch.gap,
                                 reason=p.mismatch.reason)
                    if p.mismatch is not None
                    else None
                ),
            )
            for p in progress
        ],
        recommendation=(
            RecommendationRead(
                id=recommendation.id,
                concept_id=recommendation.concept_id,
                concept_name=names.get(recommendation.concept_id, ""),
                action_type=recommendation.action_type,
                score=float(recommendation.score),
                reasoning=recommendation.reasoning,
                status=recommendation.status,
            )
            if recommendation is not None
            else None
        ),
    )


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Read-only progress: per-concept mastery, mismatches, current recommendation."""
    progress, _ = dashboard_service.build_dashboard(db, user_id=user.id, project_id=project.id)
    current = dashboard_service.current_recommendation(db, user_id=user.id, project_id=project.id)
    return _to_response(db, progress, current)


@router.post("/refresh", response_model=RecommendationRead, status_code=201)
def refresh_recommendation(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationRead:
    """Persist a fresh recommendation (previous active expires)."""
    try:
        _, signals = dashboard_service.build_dashboard(db, user_id=user.id, project_id=project.id)
        row = recommendation_service.recommend(db, user_id=user.id, project_id=project.id, signals=signals)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Recommendation provider unavailable") from e
    if row is None:
        raise HTTPException(status_code=404, detail="no scorable concepts yet")
    concept = db.get(Concept, row.concept_id)
    return RecommendationRead(
        id=row.id, concept_id=row.concept_id, concept_name=concept.title if concept else "",
        action_type=row.action_type, score=float(row.score), reasoning=row.reasoning, status=row.status,
    )


def _transition(
    db: Session, user: User, project: Project, to_status: str
) -> RecommendationRead:
    current = dashboard_service.current_recommendation(db, user_id=user.id, project_id=project.id)
    if current is None or current.status != "active":
        raise HTTPException(status_code=404, detail="no active recommendation")
    current.status = to_status
    db.commit()
    db.refresh(current)
    concept = db.get(Concept, current.concept_id)
    return RecommendationRead(
        id=current.id, concept_id=current.concept_id, concept_name=concept.title if concept else "",
        action_type=current.action_type, score=float(current.score),
        reasoning=current.reasoning, status=current.status,
    )


@router.post("/accept", response_model=RecommendationRead)
def accept_recommendation(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationRead:
    """Mark the current recommendation accepted (it sticks)."""
    return _transition(db, user, project, "accepted")


@router.post("/dismiss", response_model=RecommendationRead)
def dismiss_recommendation(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationRead:
    """Mark the current recommendation dismissed (it sticks)."""
    return _transition(db, user, project, "dismissed")
