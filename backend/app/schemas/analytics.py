from pydantic import BaseModel, Field


class ProjectAnalyticsRead(BaseModel):
    materials_total: int
    materials_by_status: dict[str, int] = Field(default_factory=dict)
    topics_count: int
    concepts_count: int
    core_concepts_count: int = 0
    quiz_attempts: int
    quiz_attempts_completed: int
    avg_mcq: float | None
    avg_applied: float | None
    avg_final: float | None = None
    evidenced_concepts: int
    streak_days: int = 0
    tutor_interactions: int = 0


class TopicMasteryRead(BaseModel):
    topic: str
    mcq: float | None = None
    applied: float | None = None


class ConfidencePointRead(BaseModel):
    concept_id: str
    concept: str
    confidence: float | None = None
    correctness: float | None = None
    attempts: int = 0
    mismatch_type: str | None = None


class TimelinePointRead(BaseModel):
    date: str
    label: str
    mcq: float | None = None
    applied: float | None = None


class BeforeNowRead(BaseModel):
    concept_id: str
    concept: str
    early_mcq: float | None = None
    early_applied: float | None = None
    current_mcq: float | None = None
    current_applied: float | None = None


class AnalyticsOverviewRead(BaseModel):
    materials_total: int = 0
    concepts_count: int = 0
    core_concepts_count: int = 0
    topics_count: int = 0
    quiz_attempts: int = 0
    quiz_attempts_completed: int = 0
    flashcards_total: int = 0
    tutor_interactions: int = 0
    assessments_total: int = 0
    avg_mcq: float | None = None
    avg_applied: float | None = None
    evidenced_concepts: int = 0
    streak_days: int = 0
    topic_mastery: list[TopicMasteryRead] = Field(default_factory=list)
    confidence_points: list[ConfidencePointRead] = Field(default_factory=list)
    timeline: list[TimelinePointRead] = Field(default_factory=list)
    before_now: list[BeforeNowRead] = Field(default_factory=list)
