import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.rate_limit import require_llm_budget
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.quiz import (
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    AttemptCompleteResponse,
    AttemptStartResponse,
    QuestionRead,
    QuizGenerateRequest,
    QuizGenerateResponse,
)
from app.services import quiz_attempt_service, quiz_generation_service
from app.services.quiz_generation_service import QuizGenerationError

router = APIRouter(prefix="/projects/{project_id}/quizzes", tags=["quizzes"])


@router.post("/generate", response_model=QuizGenerateResponse, status_code=201)
def generate_quiz(
    body: QuizGenerateRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("quiz-generate")),
) -> QuizGenerateResponse:
    """Generate a validated MCQ quiz for this project (concept or broader scope)."""
    try:
        if body.scope == "concept" and body.topic_id is None and body.subtopic_id is None:
            quiz = quiz_generation_service.generate_quiz(
                db,
                project_id=project.id,
                concept_id=body.concept_id,
                num_questions=body.num_questions,
                mode=body.mode,
                difficulty=body.difficulty,
            )
        else:
            quiz = quiz_generation_service.generate_scoped_quiz(
                db,
                project_id=project.id,
                scope=body.scope,
                topic_id=body.topic_id,
                subtopic_id=body.subtopic_id,
                concept_id=body.concept_id,
                num_questions=body.num_questions,
                mode=body.mode,
                difficulty=body.difficulty,
            )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except QuizGenerationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Quiz AI provider unavailable") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return QuizGenerateResponse(quiz_id=quiz.id, question_count=quiz.question_count)


@router.post("/{quiz_id}/attempts", response_model=AttemptStartResponse, status_code=201)
def start_attempt(
    quiz_id: str,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptStartResponse:
    """Start an attempt — questions served WITHOUT correct answers."""
    try:
        attempt = quiz_attempt_service.start_attempt(
            db, quiz_id=uuid.UUID(quiz_id), project_id=project.id, user_id=user.id
        )
    except (LookupError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    questions = quiz_attempt_service.attempt_questions(db, attempt)
    return AttemptStartResponse(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        questions=[
            QuestionRead(id=q.id, question_text=q.question_text, options=q.options,
                         difficulty=q.difficulty, concept_id=q.concept_id)
            for q in questions
        ],
    )


@router.post("/attempts/{attempt_id}/answers", response_model=AnswerSubmitResponse)
def submit_answer(
    attempt_id: str,
    body: AnswerSubmitRequest,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnswerSubmitResponse:
    """Submit one answer — correctness computed server-side, then revealed."""
    try:
        answer, correct_index = quiz_attempt_service.submit_answer(
            db,
            attempt_id=uuid.UUID(attempt_id),
            project_id=project.id,
            user_id=user.id,
            question_id=body.question_id,
            selected_index=body.selected_index,
            confidence=body.confidence,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    correct, answered = quiz_attempt_service.attempt_score(db, answer.attempt_id)
    return AnswerSubmitResponse(is_correct=answer.is_correct, correct_index=correct_index,
                                answered_count=answered, correct_count=correct)


@router.post("/attempts/{attempt_id}/complete", response_model=AttemptCompleteResponse)
def complete_attempt(
    attempt_id: str,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptCompleteResponse:
    """Complete the attempt — locks answers and stamps the score."""
    try:
        attempt = quiz_attempt_service.complete_attempt(
            db, attempt_id=uuid.UUID(attempt_id), project_id=project.id, user_id=user.id
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    correct, _ = quiz_attempt_service.attempt_score(db, attempt.id)
    total = len(quiz_attempt_service.attempt_questions(db, attempt))
    return AttemptCompleteResponse(attempt_id=attempt.id,
                                   score=float(attempt.score) if attempt.score is not None else None,
                                   correct_count=correct, total=total)
