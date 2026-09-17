import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GrowthPointRead(BaseModel):
    at: datetime
    evidence_type: str
    raw_score: float
    mcq_after: float | None
    applied_after: float | None
    quiz_after: float | None = None
    open_ended_after: float | None = None
    practice_after: float | None = None
    flashcard_after: float | None = None
    tutor_after: float | None = None
    final_after: float | None = None


class ConceptGrowthRead(BaseModel):
    concept_id: uuid.UUID
    points: list[GrowthPointRead] = Field(default_factory=list)
    mcq_trend: float | None
    applied_trend: float | None
    final_trend: float | None = None
    quiz_trend: float | None = None
    open_ended_trend: float | None = None
    practice_trend: float | None = None
    flashcard_trend: float | None = None
    tutor_trend: float | None = None
    count: int


class ConceptCurrentRead(BaseModel):
    concept_id: uuid.UUID
    title: str
    mcq: float | None
    applied: float | None
    count: int
    final: float | None = None


class ProjectGrowthRead(BaseModel):
    concepts: list[ConceptCurrentRead] = Field(default_factory=list)
    avg_mcq: float | None
    avg_applied: float | None
    avg_final: float | None = None
    evidenced_concepts: int
    total_evidence: int
    since: datetime | None
    until: datetime | None
