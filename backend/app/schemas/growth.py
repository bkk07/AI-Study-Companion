import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GrowthPointRead(BaseModel):
    at: datetime
    evidence_type: str
    raw_score: float
    mcq_after: float | None
    applied_after: float | None


class ConceptGrowthRead(BaseModel):
    concept_id: uuid.UUID
    points: list[GrowthPointRead] = Field(default_factory=list)
    mcq_trend: float | None
    applied_trend: float | None
    count: int


class ConceptCurrentRead(BaseModel):
    concept_id: uuid.UUID
    title: str
    mcq: float | None
    applied: float | None
    count: int


class ProjectGrowthRead(BaseModel):
    concepts: list[ConceptCurrentRead] = Field(default_factory=list)
    avg_mcq: float | None
    avg_applied: float | None
    evidenced_concepts: int
    total_evidence: int
    since: datetime | None
    until: datetime | None
