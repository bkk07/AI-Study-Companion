import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MismatchRead(BaseModel):
    """One flagged concept — computed, never stored."""

    mismatch_type: str
    gap: float
    reason: str


class ConceptProgressRead(BaseModel):
    """Per-concept derived state — mastery null means no evidence yet."""

    concept_id: uuid.UUID
    title: str
    topic: str
    subtopic: str
    mcq: float | None
    applied: float | None
    mcq_count: int
    applied_count: int
    last_evidence_at: datetime | None
    mismatch: MismatchRead | None


class RecommendationRead(BaseModel):
    """Current (or most recent) recommendation with its deterministic reason."""

    id: uuid.UUID
    concept_id: uuid.UUID
    concept_name: str
    action_type: str
    score: float
    reasoning: str
    status: str


class DashboardResponse(BaseModel):
    concepts: list[ConceptProgressRead] = Field(default_factory=list)
    recommendation: RecommendationRead | None = None
