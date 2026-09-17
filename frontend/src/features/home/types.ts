export type HomeContinue = {
  space_id: string
  space_name: string
  project_id: string
  project_name: string
  tab: string
  touched_at: string
}

export type HomeProject = {
  id: string
  name: string
  space_id: string
  space_name: string
  progress_pct: number | null
  due_count: number
  attention_count: number
  touched_at: string | null
}

export type HomeAttention = {
  project_id: string
  project_name: string
  space_id: string
  concept_id: string
  concept_title: string
  mismatch_type: string
  gap: number | null
  reason: string
}

export type HomeAction = {
  project_id: string
  project_name: string
  space_id: string
  concept_id: string | null
  concept_title: string | null
  action_type: string
  score: number
  reasoning: string
  status: string
}

export type HomeRead = {
  continue: HomeContinue | null
  recent_projects: HomeProject[]
  stats: { streak_days: number; due_total: number; events_week: number; evidence_total: number }
  attention: HomeAttention[]
  next_actions: HomeAction[]
  week_activity: { day: string; events: number }[]
}
