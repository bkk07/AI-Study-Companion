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
from app.schemas.tutor import (
    ChatSendRequest,
    ChatSendResponse,
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    QuizPlanRequest,
    QuizPlanResponse,
    TutorAskRequest,
    TutorAskResponse,
    TutorCheckRequest,
    TutorCheckResponse,
    TutorMessageRead,
)
from app.services.open_ended_assessment_service import OpenEndedAssessmentError
from app.services import tutor_conversation_service, tutor_service
from app.services.tutor_conversation_service import citation_models
from app.services.tutor_service import TutorProviderError

router = APIRouter(prefix="/projects/{project_id}/tutor", tags=["tutor"])


@router.post("/ask", response_model=TutorAskResponse)
def ask_tutor(
    body: TutorAskRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("tutor")),
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
    except TutorProviderError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider returned an unusable response") from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider unavailable") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _convo_or_404(db: Session, conversation_id: uuid.UUID, project: Project, user: User):
    convo = tutor_conversation_service.get_owned_conversation(
        db, conversation_id=conversation_id, project_id=project.id, user_id=user.id
    )
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationRead]:
    """Newest-first chat threads for this project + user."""
    return [
        ConversationRead(
            id=c.id, title=c.title, message_count=n,
            created_at=c.created_at, updated_at=c.updated_at,
        )
        for c, n in tutor_conversation_service.list_conversations(
            db, project_id=project.id, user_id=user.id
        )
    ]


@router.post("/conversations", response_model=ConversationRead, status_code=201)
def create_conversation(
    body: ConversationCreate,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationRead:
    """Start an empty thread (chatting begins on the first message)."""
    convo = tutor_conversation_service.create_conversation(db, project=project, user=user, title=body.title)
    return ConversationRead(
        id=convo.id, title=convo.title, message_count=0,
        created_at=convo.created_at, updated_at=convo.updated_at,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Full thread with ordered messages (owner + project scoped)."""
    convo = _convo_or_404(db, conversation_id, project, user)
    return ConversationDetail(
        id=convo.id,
        title=convo.title,
        messages=[
            TutorMessageRead(
                id=m.id, role=m.role, content=m.content, supported=m.supported,
                citations=citation_models(m.citations), follow_ups=list(m.follow_ups or []),
                created_at=m.created_at,
            )
            for m in tutor_conversation_service.get_messages(db, convo.id)
        ],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=ChatSendResponse)
def send_chat_message(
    conversation_id: uuid.UUID,
    body: ChatSendRequest,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("tutor")),
) -> ChatSendResponse:
    """Ask inside a thread — both sides persisted, thread retitled on first exchange."""
    convo = _convo_or_404(db, conversation_id, project, user)
    try:
        user_msg, assistant_msg, response = tutor_conversation_service.send_message(
            db, convo=convo, question=body.question, concept_id=body.concept_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except TutorProviderError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider returned an unusable response") from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider unavailable") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ChatSendResponse(
        conversation_id=convo.id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
        answer=response.answer,
        supported=response.supported,
        citations=response.citations,
        follow_ups=response.follow_ups,
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a thread and its messages (owner + project scoped)."""
    convo = _convo_or_404(db, conversation_id, project, user)
    tutor_conversation_service.delete_conversation(db, convo)
    return None


@router.post("/conversations/{conversation_id}/checks", response_model=TutorCheckResponse, status_code=201)
def submit_tutor_check(
    conversation_id: uuid.UUID,
    body: TutorCheckRequest,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("explain-back")),
) -> TutorCheckResponse:
    """Grade a tutor follow-up demonstration and bank `tutor` mastery evidence.

    Production caller for ``mastery_service.record_tutor_evidence``: requires
    a grounded (supported + cited) assistant answer in this thread plus an
    explicit in-project concept. Plain chat stays evidence-free; only this
    graded check writes ``mastery_evidence`` (append-only, 1/day/concept).
    """
    convo = _convo_or_404(db, conversation_id, project, user)
    try:
        evidence, grade = tutor_conversation_service.submit_tutor_check(
            db,
            convo=convo,
            assistant_message_id=body.assistant_message_id,
            concept_id=body.concept_id,
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
    return TutorCheckResponse(
        evidence_id=evidence.id,
        concept_id=evidence.concept_id,
        score=grade.score,
        verdict=grade.verdict,
        feedback=grade.feedback,
    )


@router.post("/quiz-plan", response_model=QuizPlanResponse)
def quiz_plan(
    body: QuizPlanRequest,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
    _: None = Depends(require_llm_budget("tutor")),
) -> QuizPlanResponse:
    """Map recent prompts to quiz concepts for the quiz-me confirm UI."""
    try:
        plan = tutor_service.plan_quiz(db, project_id=project.id, questions=body.questions)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except TutorProviderError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider returned an unusable response") from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Tutor AI provider unavailable") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return QuizPlanResponse(label=plan.label, concept_ids=list(plan.concept_ids))
