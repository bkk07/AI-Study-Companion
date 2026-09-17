import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminOverview(BaseModel):
    """Global operational counts — no per-user PII, read-only."""

    users: int
    spaces: int
    projects: int
    materials: int
    quizzes: int
    quiz_attempts: int
    evidence_rows: int
    recommendations: int
    # Blueprint global summary row: this-week activity + spend.
    quiz_attempts_week: int
    cost_week_usd: float | None


class AdminUserRead(BaseModel):
    """User row for the admin list: identity + project count + last tracked activity."""

    id: uuid.UUID
    email: str
    is_admin: bool
    created_at: datetime
    project_count: int
    last_active: datetime | None

    model_config = {"from_attributes": True}


class UsersPage(BaseModel):
    items: list[AdminUserRead]
    total: int
    limit: int
    offset: int


class ActivityEventRead(BaseModel):
    """One learning event for the admin timeline — payloads are counts/scores only."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    project_id: uuid.UUID | None
    space_id: uuid.UUID | None
    event_type: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    payload: dict
    idempotency_key: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityPage(BaseModel):
    items: list[ActivityEventRead]
    total: int
    limit: int
    offset: int


class AIUsageDayRow(BaseModel):
    day: str
    feature: str
    provider: str
    model: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None
    avg_latency_ms: float | None


class AIUsageTopError(BaseModel):
    error_type: str
    count: int


class AIUsageSummary(BaseModel):
    """Tokens + cost grouped by feature × model × day, with latency and errors."""

    calls: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None
    error_rate: float
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    top_errors: list[AIUsageTopError]
    rows: list[AIUsageDayRow]


class JourneyProject(BaseModel):
    id: uuid.UUID
    name: str
    space_id: uuid.UUID
    created_at: datetime


class JourneyAttempt(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    score: float | None
    started_at: datetime | None
    completed_at: datetime | None


class MasterySummary(BaseModel):
    evidence_rows: int
    by_type: dict[str, int]
    avg_score: float | None


class SpendSummary(BaseModel):
    calls: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None


class UserJourney(BaseModel):
    """Everything needed to inspect one learner: projects, timeline, attempts, mastery, spend."""

    user_id: uuid.UUID
    email: str
    projects: list[JourneyProject]
    recent_events: list[ActivityEventRead]
    recent_attempts: list[JourneyAttempt]
    mastery: MasterySummary
    spend: SpendSummary


class HealthJob(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    material_id: uuid.UUID | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HealthLLMError(BaseModel):
    id: uuid.UUID
    feature: str
    provider: str
    model: str
    error_type: str | None
    http_status: int | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobsByStatus(BaseModel):
    status: str
    count: int


class HealthRead(BaseModel):
    """Which workflow failed / why was it slow (§14): recent job + LLM failures."""

    failed_jobs: list[HealthJob]
    failed_llm_calls: list[HealthLLMError]
    failed_job_count_24h: int
    failed_llm_count_24h: int
    jobs_by_status: list[JobsByStatus]
