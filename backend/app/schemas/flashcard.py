import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeckBuildRequest(BaseModel):
    """Scope for deck building — one scope max; none = project.

    concept_ids carries an explicit multi-select (tutor flows); the single
    ids keep the existing single-scope UI working.
    """

    subtopic_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    concept_id: uuid.UUID | None = None
    concept_ids: list[uuid.UUID] | None = None


class DeckBuildResponse(BaseModel):
    created: int
    total: int


class FlashcardRead(BaseModel):
    id: uuid.UUID
    concept_id: uuid.UUID
    front: str
    back: str
    repetitions: int
    lapses: int
    interval_days: int
    efactor: float
    next_review_at: datetime | None = None
    total_reviews: int
    correct_reviews: int
    due: bool = False


class FlashcardListRead(BaseModel):
    cards: list[FlashcardRead] = Field(default_factory=list)
    due_count: int = 0


class ReviewRequest(BaseModel):
    grade: str = Field(pattern="^(again|hard|good|easy)$")


class ReviewResponse(BaseModel):
    card: FlashcardRead
    quality: int
    score: float
