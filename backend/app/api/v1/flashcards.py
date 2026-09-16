import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.project import Project
from app.models.user import User
from app.schemas.flashcard import (
    DeckBuildRequest,
    DeckBuildResponse,
    FlashcardListRead,
    FlashcardRead,
    ReviewRequest,
    ReviewResponse,
)
from app.services import flashcard_service
from app.services.flashcard_service import GRADE_QUALITY

router = APIRouter(prefix="/projects/{project_id}/flashcards", tags=["flashcards"])


def _read(card, now: datetime) -> FlashcardRead:
    return FlashcardRead(
        id=card.id,
        concept_id=card.concept_id,
        front=card.front,
        back=card.back,
        repetitions=card.repetitions,
        lapses=card.lapses,
        interval_days=card.interval_days,
        efactor=float(card.efactor),
        next_review_at=card.next_review_at,
        total_reviews=card.total_reviews,
        correct_reviews=card.correct_reviews,
        due=card.next_review_at is None or card.next_review_at <= now,
    )


@router.post("/decks", response_model=DeckBuildResponse, status_code=201)
def build_deck(
    body: DeckBuildRequest,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeckBuildResponse:
    """Create missing cards for CORE targets in scope (idempotent)."""
    _ = user
    try:
        result = flashcard_service.build_deck(
            db, project_id=project.id,
            subtopic_id=body.subtopic_id, topic_id=body.topic_id,
            concept_id=body.concept_id,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return DeckBuildResponse(**result)


@router.get("", response_model=FlashcardListRead)
def list_cards(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    subtopic_id: uuid.UUID | None = None,
    topic_id: uuid.UUID | None = None,
    concept_id: uuid.UUID | None = None,
    due_only: bool = False,
    limit: int = Query(default=100, ge=1, le=100),
) -> FlashcardListRead:
    """Cards in scope, due-first. due_count covers the whole project."""
    _ = user
    now = datetime.now(timezone.utc)
    try:
        cards = flashcard_service.list_cards(
            db, project_id=project.id, subtopic_id=subtopic_id,
            topic_id=topic_id, concept_id=concept_id,
            due_only=due_only, limit=limit, now=now,
        )
        due_count = flashcard_service.count_due(db, project_id=project.id, now=now)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FlashcardListRead(cards=[_read(c, now) for c in cards], due_count=due_count)


@router.post("/{card_id}/review", response_model=ReviewResponse)
def review_card(
    card_id: uuid.UUID,
    body: ReviewRequest,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    """Grade one review — reschedules the card and banks mastery evidence."""
    try:
        card = flashcard_service.review_card(
            db, project_id=project.id, user_id=user.id,
            card_id=card_id, grade=body.grade,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    quality = GRADE_QUALITY[body.grade]
    return ReviewResponse(
        card=_read(card, datetime.now(timezone.utc)),
        quality=quality,
        score=float(quality * 20),
    )
