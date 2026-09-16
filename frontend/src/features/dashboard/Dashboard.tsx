import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, Compass, Sparkles } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Badge, Button, EmptyState, ErrorBox, LoadingState, ProgressBar } from "@/components/ui"
import { statusTint } from "@/features/quiz/ConceptDetail"

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
  status: string
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

function MasteryRow({ label, value, count }: { label: string; value: number | null; count: number }) {
  return (
    <div className="mt-2">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-semibold text-muted-foreground">{label}</span>
        <span className="font-bold">{value === null ? "No evidence" : `${value.toFixed(0)} · ${count} evidence`}</span>
      </div>
      <ProgressBar value={value} className="mt-1" />
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

  if (loading) return <LoadingState text="Loading progress…" />
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />
  if (!data) return null

  const rec = data.recommendation

  return (
    <div className="space-y-5">
      {/* Recommendation spotlight */}
      <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 p-[1.5px] shadow-soft">
        <div className="rounded-2xl bg-card p-5">
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.12em] text-violet-600">
            <Compass className="h-4 w-4" /> Up next for you
          </p>
          {!rec ? (
            <div className="mt-2">
              <p className="font-bold">No recommendation yet</p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Generate one from your current progress and always know what to study next.
              </p>
              <Button onClick={() => void postAction("refresh")} disabled={acting} size="sm" className="mt-3">
                <Sparkles className="h-4 w-4" /> {acting ? "Working…" : "Generate recommendation"}
              </Button>
            </div>
          ) : (
            <div className="mt-2">
              <p className="text-lg font-extrabold tracking-tight">
                {actionLabel(rec.action_type)}: <span className="text-gradient">{rec.concept_name}</span>
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{rec.reasoning}</p>
              <p className="mt-2 flex items-center gap-2 text-xs">
                <Badge tint="violet">Score {rec.score.toFixed(0)}</Badge>
                <Badge tint={rec.status === "active" ? "emerald" : "muted"}>{rec.status}</Badge>
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button onClick={() => void postAction("refresh")} disabled={acting} size="sm">
                  Refresh
                </Button>
                {rec.status === "active" && (
                  <>
                    <Button onClick={() => void postAction("accept")} disabled={acting} size="sm" variant="secondary">
                      Accept
                    </Button>
                    <Button onClick={() => void postAction("dismiss")} disabled={acting} size="sm" variant="outline">
                      Dismiss
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {data.concepts.length === 0 ? (
        <EmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title="Mastery will appear here"
          hint="Upload material and wait for processing, then answer a quiz or explain a concept."
        />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {data.concepts.map((c) => (
            <li key={c.concept_id} className="rounded-2xl border bg-card p-4 shadow-soft">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-bold">{c.title}</p>
                <Badge tint={statusTint(c.status)}>{c.status}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {c.topic} › {c.subtopic}
              </p>
              <MasteryRow label="Recognition" value={c.mcq} count={c.mcq_count} />
              <MasteryRow label="Applied" value={c.applied} count={c.applied_count} />
              {c.mismatch && (
                <div className="mt-2.5 flex gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-amber-700">
                      {mismatchLabel(c.mismatch.mismatch_type)}
                    </p>
                    <p className="mt-0.5 text-xs text-amber-900/70">{c.mismatch.reason}</p>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
