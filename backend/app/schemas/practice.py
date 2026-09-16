import uuid

from pydantic import BaseModel, Field


class PracticeCandidateRead(BaseModel):
    """One Recommended-tab card — pure derivation, nothing persisted."""

    concept_id: uuid.UUID
    name: str
    lo_type: str | None = None
    mastery: float | None = None
    status: str
    score: float | None = None
    reasoning: str
    fallback: bool = False


class PracticeRecommendationsRead(BaseModel):
    """Top-N practice targets + optional neutral no-history fallback."""

    items: list[PracticeCandidateRead] = Field(default_factory=list)
    fallback: PracticeCandidateRead | None = None
