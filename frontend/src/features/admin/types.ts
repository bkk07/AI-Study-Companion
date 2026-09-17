export type AdminUser = {
  id: string
  email: string
  is_admin: boolean
  created_at: string
  project_count: number
  last_active: string | null
}

export type Overview = {
  users: number
  spaces: number
  projects: number
  materials: number
  quizzes: number
  quiz_attempts: number
  evidence_rows: number
  recommendations: number
  quiz_attempts_week: number
  cost_week_usd: number | null
}

export type ActivityEvent = {
  id: string
  user_id: string | null
  project_id: string | null
  space_id: string | null
  event_type: string
  entity_type: string | null
  entity_id: string | null
  payload: Record<string, unknown>
  idempotency_key: string
  created_at: string
}

export type ActivityPage = {
  items: ActivityEvent[]
  total: number
  limit: number
  offset: number
}

export type AIUsageDayRow = {
  day: string
  feature: string
  provider: string
  model: string
  calls: number
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number | null
  avg_latency_ms: number | null
}

export type AIUsageSummary = {
  calls: number
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number | null
  error_rate: number
  latency_p50_ms: number | null
  latency_p95_ms: number | null
  top_errors: { error_type: string; count: number }[]
  rows: AIUsageDayRow[]
}

export type UserJourney = {
  user_id: string
  email: string
  projects: { id: string; name: string; space_id: string; created_at: string }[]
  recent_events: ActivityEvent[]
  recent_attempts: {
    id: string
    quiz_id: string
    score: number | null
    started_at: string | null
    completed_at: string | null
  }[]
  mastery: { evidence_rows: number; by_type: Record<string, number>; avg_score: number | null }
  spend: { calls: number; prompt_tokens: number; completion_tokens: number; cost_usd: number | null }
}

export type Health = {
  failed_jobs: {
    id: string
    job_type: string
    status: string
    material_id: string | null
    error: string | null
    created_at: string
    updated_at: string
  }[]
  failed_llm_calls: {
    id: string
    feature: string
    provider: string
    model: string
    error_type: string | null
    http_status: number | null
    latency_ms: number | null
    created_at: string
  }[]
  failed_job_count_24h: number
  failed_llm_count_24h: number
  jobs_by_status: { status: string; count: number }[]
}

export const EVENT_TYPES = [
  "project.created",
  "material.uploaded",
  "material.ready",
  "material.failed",
  "tutor.message",
  "quiz.started",
  "quiz.completed",
  "question.answered",
  "assessment.completed",
  "mastery.updated",
  "recommendation.generated",
] as const
