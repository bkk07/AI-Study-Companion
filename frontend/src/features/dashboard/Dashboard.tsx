import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, BarChart2, Brain, CreditCard, FileText, HelpCircle, Play } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { ErrorBox, LoadingState, MasteryBadge, StatCard, masteryLevelFor, type MasteryLevel } from "@/components/ui"

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

function toMasteryLevel(status: string, value: number | null): MasteryLevel {
  if (status === "Mastered" || status === "Strong") return "mastered"
  if (status === "Developing") return "developing"
  if (status === "Needs Practice") return "weak"
  return masteryLevelFor(value)
}

function mismatchLabel(type: string): string {
  if (type === "mcq_high_applied_low") return "Recognition outruns understanding"
  if (type === "overconfident") return "Overconfident"
  if (type === "underconfident") return "Underconfident"
  return type
}

export function Dashboard({ projectId, overviewMode = false }: { projectId: string; overviewMode?: boolean }) {
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
  const mastered = data.concepts.filter((c) => c.status === "Mastered" || c.status === "Strong").length
  const developing = data.concepts.filter((c) => c.status === "Developing").length
  const weak = data.concepts.filter((c) => c.status === "Needs Practice").length
  const mismatches = data.concepts.filter((c) => c.mismatch).length
  const avgMcq =
    data.concepts.length > 0
      ? data.concepts.reduce((s, c) => s + (c.mcq ?? 0), 0) / data.concepts.length
      : null
  const withEvidence = data.concepts.filter((c) => c.mcq !== null || c.applied !== null).length

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Concepts" value={data.concepts.length} icon={<Brain size={18} />} accent="indigo" />
        <StatCard label="With Evidence" value={withEvidence} icon={<FileText size={18} />} accent="slate" />
        <StatCard label="Quiz Targets" value={data.concepts.length} icon={<HelpCircle size={18} />} accent="slate" />
        <StatCard label="Flashcards" value="—" icon={<CreditCard size={18} />} accent="slate" />
        <StatCard
          label="Avg Mastery"
          value={avgMcq !== null ? `${Math.round(avgMcq)}%` : "—"}
          icon={<BarChart2 size={18} />}
          accent="green"
          sub="MCQ + Applied"
        />
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Mastered", value: mastered, color: "text-green-700", bg: "bg-green-50 border-green-100" },
          { label: "Developing", value: developing, color: "text-amber-700", bg: "bg-amber-50 border-amber-100" },
          { label: "Weak", value: weak, color: "text-red-700", bg: "bg-red-50 border-red-100" },
          { label: "Mismatches", value: mismatches, color: "text-orange-700", bg: "bg-orange-50 border-orange-100" },
        ].map((item) => (
          <div key={item.label} className={`rounded-lg border px-4 py-3 ${item.bg}`}>
            <div className={`font-mono-data text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="mt-0.5 text-xs text-slate-500">{item.label}</div>
          </div>
        ))}
      </div>

      {rec ? (
        <div className="rounded-xl bg-indigo-600 p-6 text-white">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-300">
            Primary Recommendation
          </div>
          <h3 className="mb-1 text-lg font-semibold">
            {actionLabel(rec.action_type)}: {rec.concept_name}
          </h3>
          <p className="mb-4 text-sm text-indigo-200">{rec.reasoning}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void postAction("refresh")}
              disabled={acting}
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
            >
              {acting ? "Working…" : "Refresh"}
            </button>
            {rec.status === "active" && (
              <>
                <button
                  type="button"
                  onClick={() => void postAction("accept")}
                  disabled={acting}
                  className="rounded-lg border border-indigo-400 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
                >
                  Accept
                </button>
                <button
                  type="button"
                  onClick={() => void postAction("dismiss")}
                  disabled={acting}
                  className="rounded-lg border border-indigo-400 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
                >
                  Dismiss
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Up next for you</div>
          <h3 className="text-base font-semibold text-slate-900">No recommendation yet</h3>
          <p className="mt-1 text-sm text-slate-500">
            Generate one from your current progress and always know what to study next.
          </p>
          <button
            type="button"
            onClick={() => void postAction("refresh")}
            disabled={acting}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            <Play size={14} /> {acting ? "Working…" : "Generate recommendation"}
          </button>
        </div>
      )}

      {data.concepts.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center">
          <p className="font-semibold text-slate-800">Mastery will appear here</p>
          <p className="mt-1 text-sm text-slate-500">
            Upload material and wait for processing, then answer a quiz or explain a concept.
          </p>
        </div>
      ) : (
        <div>
          <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Concepts That Need Attention
          </div>
          <div className="space-y-3">
            {data.concepts.slice(0, overviewMode ? 6 : 20).map((c) => (
              <div key={c.concept_id} className="rounded-xl border border-slate-200 bg-white p-5">
                <div className="flex items-start gap-4">
                  <div className="flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-800">{c.title}</span>
                      <MasteryBadge level={toMasteryLevel(c.status, c.mcq)} />
                    </div>
                    <div className="text-xs text-slate-400">
                      {c.topic} → {c.subtopic}
                    </div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500">Recognition</span>
                          <span className="font-mono-data font-semibold text-slate-700">
                            {c.mcq === null ? "—" : `${Math.round(c.mcq)}%`}
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-indigo-500"
                            style={{ width: `${c.mcq ?? 0}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500">Applied</span>
                          <span className="font-mono-data font-semibold text-slate-700">
                            {c.applied === null ? "—" : `${Math.round(c.applied)}%`}
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-emerald-500"
                            style={{ width: `${c.applied ?? 0}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    {c.mismatch && (
                      <div className="mt-3 flex gap-2 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2">
                        <AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-600" />
                        <div>
                          <p className="text-xs font-semibold text-amber-700">
                            {mismatchLabel(c.mismatch.mismatch_type)}
                          </p>
                          <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{c.mismatch.reason}</p>
                        </div>
                      </div>
                    )}
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
                    c.status === "Mastered" ? "bg-green-50 text-green-700 ring-green-200"
                    : c.status === "Strong" ? "bg-sky-50 text-sky-700 ring-sky-200"
                    : c.status === "Developing" ? "bg-amber-50 text-amber-700 ring-amber-200"
                    : c.status === "Needs Practice" ? "bg-red-50 text-red-700 ring-red-200"
                    : "bg-slate-50 text-slate-500 ring-slate-200"
                  }`}>
                    {c.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {rec && (
        <div>
          <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Today&apos;s Recommended Plan
          </div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-5">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm">
                <HelpCircle size={16} className="text-indigo-600" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-slate-800">
                  {actionLabel(rec.action_type)} — {rec.concept_name}
                </div>
                <div className="mt-2 flex items-start gap-1">
                  <span className="shrink-0 text-xs font-medium text-slate-500">Why?</span>
                  <p className="text-xs leading-relaxed text-slate-500">{rec.reasoning}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
