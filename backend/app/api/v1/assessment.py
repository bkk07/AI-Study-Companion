import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.schemas.assessment import OpenEndedGradeRequest, OpenEndedGradeResponse
from app.services import open_ended_assessment_service
from app.services.open_ended_assessment_service import OpenEndedAssessmentError

router = APIRouter(prefix="/projects/{project_id}/assessment", tags=["assessment"])


@router.post("/open-ended", response_model=OpenEndedGradeResponse)
def grade_open_ended(
    body: OpenEndedGradeRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
) -> OpenEndedGradeResponse:
    """Grade a free-text answer against one concept — evidence source, never mutates mastery."""
    try:
        grade = open_ended_assessment_service.grade_open_ended(
            db,
            project_id=project.id,
            concept_id=body.concept_id,
            answer_text=body.answer_text,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OpenEndedAssessmentError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Assessment AI provider unavailable") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return OpenEndedGradeResponse(
        concept_id=body.concept_id,
        score=grade.score,
        verdict=grade.verdict,
        feedback=grade.feedback,
    )
