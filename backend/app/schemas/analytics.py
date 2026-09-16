from pydantic import BaseModel, Field


class ProjectAnalyticsRead(BaseModel):
    materials_total: int
    materials_by_status: dict[str, int] = Field(default_factory=dict)
    topics_count: int
    concepts_count: int
    quiz_attempts: int
    quiz_attempts_completed: int
    avg_mcq: float | None
    avg_applied: float | None
    evidenced_concepts: int
    tutor_interactions: None = None
