import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class HomeContinue(BaseModel):
    space_id: uuid.UUID
    space_name: str
    project_id: uuid.UUID
    project_name: str
    tab: str
    touched_at: datetime


class HomeProject(BaseModel):
    id: uuid.UUID
    name: str
    space_id: uuid.UUID
    space_name: str
    progress_pct: float | None
    due_count: int
    attention_count: int
    touched_at: datetime | None


class HomeAttention(BaseModel):
    project_id: uuid.UUID
    project_name: str
    space_id: uuid.UUID
    concept_id: uuid.UUID
    concept_title: str
    mismatch_type: str
    gap: float | None
    reason: str


class HomeAction(BaseModel):
    project_id: uuid.UUID
    project_name: str
    space_id: uuid.UUID
    concept_id: uuid.UUID | None
    concept_title: str | None
    action_type: str
    score: float
    reasoning: str
    status: str


class HomeStats(BaseModel):
    streak_days: int
    due_total: int
    events_week: int
    evidence_total: int


class HomeDay(BaseModel):
    day: str
    events: int


class HomeRead(BaseModel):
    continue_: HomeContinue | None = Field(default=None, alias="continue")
    recent_projects: list[HomeProject]
    stats: HomeStats
    attention: list[HomeAttention]
    next_actions: list[HomeAction]
    week_activity: list[HomeDay]

    model_config = {"populate_by_name": True}
