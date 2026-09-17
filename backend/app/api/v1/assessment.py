import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.rate_limit import require_llm_budget
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.assessment import (
    ExplainBackRequest,
    ExplainBackResponse,
    OpenEndedGenerateRequest,
    OpenEndedGenerateResponse,
    OpenEndedGradeRequest,
    OpenEndedGradeResponse,
)
from app.services import explain_it_back_service, open_ended_assessment_service
from app.services.open_ended_assessment_service import OpenEndedAssessmentError

router = APIRouter(prefix="/projects/{project_id}/assessment", tags=["assessment"])


@router.post("/open-ended/generate", response_model=OpenEndedGenerateResponse, status_code=201)
def generate_open_ended_question(
    body: OpenEndedGenerateRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("assessment")),
) -> OpenEndedGenerateResponse:
    """Generate one open-ended question for a topic/subtopic/concept scope."""
    try:
        question = open_ended_assessment_service.generate_open_ended_question(
            db,
            project_id=project.id,
            scope=body.scope,
            topic_id=body.topic_id,
            subtopic_id=body.subtopic_id,
            concept_id=body.concept_id,
            topic_ids=body.topic_ids,
            subtopic_ids=body.subtopic_ids,
            concept_ids=body.concept_ids,
            difficulty=body.difficulty,
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
    return OpenEndedGenerateResponse(
        question_text=question.question_text,
        concept_id=question.concept_id,
        scope_label=question.scope_label,
        difficulty=question.difficulty,
    )


@router.post("/open-ended", response_model=OpenEndedGradeResponse)
def grade_open_ended(
    body: OpenEndedGradeRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("assessment")),
) -> OpenEndedGradeResponse:
    """Grade a free-text answer against one concept — evidence source, never mutates mastery."""
    try:
        grade = open_ended_assessment_service.grade_open_ended(
            db,
            project_id=project.id,
            concept_id=body.concept_id,
            answer_text=body.answer_text,
            question_text=body.question_text,
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
        strengths=list(grade.strengths),
        missing_points=list(grade.missing_points),
        suggestions=list(grade.suggestions),
    )


@router.post("/explain-back", response_model=ExplainBackResponse, status_code=201)
def submit_explanation(
    body: ExplainBackRequest,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("explain-back")),
) -> ExplainBackResponse:
    """Grade an explanation and append it as `explain_back` evidence."""
    try:
        evidence, grade = explain_it_back_service.submit_explanation(
            db,
            project_id=project.id,
            concept_id=body.concept_id,
            user_id=user.id,
            explanation_text=body.explanation_text,
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
    return ExplainBackResponse(
        evidence_id=evidence.id,
        concept_id=body.concept_id,
        score=grade.score,
        verdict=grade.verdict,
        feedback=grade.feedback,
    )
