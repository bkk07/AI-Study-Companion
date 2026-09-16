import { useCallback, useEffect, useState } from "react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"

type Mismatch = {
  mismatch_type: string
  gap: number
  reason: string
}

type ConceptProgress = {
  concept_id: string
  title: string
  topic: string
  subtopic: string
  mcq: number | null
  applied: number | null
  mcq_count: number
  applied_count: number
  last_evidence_at: string | null
  mismatch: Mismatch | null
}

type Recommendation = {
  id: string
  concept_id: string
  concept_name: string
  action_type: string
  score: number
  reasoning: string
  status: string
}

type DashboardData = {
  concepts: ConceptProgress[]
  recommendation: Recommendation | null
}

const ACTION_LABELS: Record<string, string> = {
  ask_tutor: "Ask the tutor",
  targeted_quiz: "Take a targeted quiz",
  explain_back: "Explain it back",
  review_material: "Review the material",
  exam_mode: "Run an exam-mode session",
}

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action
}

function mismatchLabel(type: string): string {
  if (type === "mcq_high_applied_low") return "Recognition outruns understanding"
  if (type === "overconfident") return "Overconfident"
  if (type === "underconfident") return "Underconfident"
  return type
}

function MasteryBar({ label, value, count }: { label: string; value: number | null; count: number }) {
  if (value === null) {
    return (
      <div className="mt-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{label}</span>
          <span>No evidence yet</span>
        </div>
        <div className="mt-1 h-2 rounded bg-muted" />
      </div>
    )
  }
  return (
    <div className="mt-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>
          {value.toFixed(1)} ({count} evidence)
        </span>
      </div>
      <div className="mt-1 h-2 rounded bg-muted">
        <div className="h-2 rounded bg-primary" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  )
}

export function Dashboard({ projectId }: { projectId: string }) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<DashboardData>(`/projects/${projectId}/dashboard`)
      setData(res.data)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 404) setError("Project not found for this dashboard.")
      else setError(detail ?? "Failed to load progress.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void load()
  }, [load])

  async function postAction(path: string) {
    if (acting) return
    setActing(true)
    setError(null)
    try {
      await apiClient.post(`/projects/${projectId}/dashboard/${path}`)
      await load()
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 404 && path !== "refresh") setError("No active recommendation to update.")
      else if (status === 404) setError("Nothing scorable yet — answer quizzes or explain a concept first.")
      else setError(detail ?? "Action failed.")
    } finally {
      setActing(false)
    }
  }

  if (loading) return <p className="mt-2 text-sm text-muted-foreground">Loading progress…</p>
  if (error)
    return (
      <div className="mt-2">
        <p className="text-sm text-destructive">{error}</p>
        <button onClick={() => void load()} className="mt-1 text-sm text-primary hover:underline">
          Retry
        </button>
      </div>
    )
  if (!data) return null

  const rec = data.recommendation

  return (
    <div className="mt-2 space-y-4">
      {data.concepts.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No learning structure yet — upload material and wait for processing, then your mastery will appear here.
        </p>
      ) : (
        <ul className="space-y-3">
          {data.concepts.map((c) => (
            <li key={c.concept_id} className="rounded-md border bg-card px-3 py-2">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-sm font-medium">{c.title}</p>
                <p className="text-xs text-muted-foreground">
                  {c.topic} › {c.subtopic}
                </p>
              </div>
              <MasteryBar label="Recognition (MCQ)" value={c.mcq} count={c.mcq_count} />
              <MasteryBar label="Applied" value={c.applied} count={c.applied_count} />
              {c.mismatch && (
                <div className="mt-2 rounded-md border border-amber-500/50 bg-amber-500/10 px-2 py-1.5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">
                    {mismatchLabel(c.mismatch.mismatch_type)}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{c.mismatch.reason}</p>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-md border bg-card px-3 py-2">
        <p className="text-sm font-medium">Current recommendation</p>
        {!rec ? (
          <div className="mt-1">
            <p className="text-sm text-muted-foreground">
              No recommendation yet — generate one from your current progress.
            </p>
            <button
              onClick={() => void postAction("refresh")}
              disabled={acting}
              className="mt-2 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
            >
              Generate recommendation
            </button>
          </div>
        ) : (
          <div className="mt-1">
            <p className="text-sm">
              {actionLabel(rec.action_type)}: <span className="font-medium">{rec.concept_name}</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{rec.reasoning}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Score {rec.score.toFixed(1)} · Status {rec.status}
            </p>
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => void postAction("refresh")}
                disabled={acting}
                className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
              >
                Refresh
              </button>
              {rec.status === "active" && (
                <>
                  <button
                    onClick={() => void postAction("accept")}
                    disabled={acting}
                    className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => void postAction("dismiss")}
                    disabled={acting}
                    className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
                  >
                    Dismiss
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
