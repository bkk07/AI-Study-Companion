import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MismatchRead(BaseModel):
    """One flagged concept — computed, never stored."""

    mismatch_type: str
    gap: float
    reason: str


class StreamMasteryRead(BaseModel):
    """One Plan A activity stream — value None means no evidence yet."""

    value: float | None = None
    count: int = 0


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
    status: str
    mismatch: MismatchRead | None
    avg_confidence: float | None = None
    accuracy: float | None = None
    evaluated_count: int = 0
    # Plan A: weighted final + per-stream breakdown + evidence-amount flag
    # ("none" / "low" / "ok"). Additive — legacy mcq/applied fields above
    # are unchanged.
    final_mastery: float | None = None
    evidence_confidence: str = "none"
    streams: dict[str, StreamMasteryRead] = Field(default_factory=dict)


class RecommendationRead(BaseModel):
    """Current (or most recent) recommendation with its deterministic reason."""

    id: uuid.UUID
    concept_id: uuid.UUID
    concept_name: str
    action_type: str
    score: float
    reasoning: str
    status: str
    # Blueprint §16 breadcrumb: Topic > Subtopic > Concept path for the
    # recommended concept. Additive defaults keep old clients/tests working.
    topic: str = ""
    subtopic: str = ""
    concept_path: str = ""


class DashboardResponse(BaseModel):
    concepts: list[ConceptProgressRead] = Field(default_factory=list)
    recommendation: RecommendationRead | None = None
