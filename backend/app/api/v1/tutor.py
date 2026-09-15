import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.schemas.tutor import TutorAskRequest, TutorAskResponse
from app.services import tutor_service

router = APIRouter(prefix="/projects/{project_id}/tutor", tags=["tutor"])


@router.post("/ask", response_model=TutorAskResponse)
def ask_tutor(
    body: TutorAskRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
) -> TutorAskResponse:
    """Ask a project-scoped question — grounded answer or explicit unsupported."""
    try:
        return tutor_service.ask_question(
            db,
            project_id=project.id,
            question=body.question,
            concept_id=body.concept_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider unavailable") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
