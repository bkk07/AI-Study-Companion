import { useCallback, useEffect, useState } from "react"
import {
  AlertTriangle,
  BarChart2,
  Brain,
  CreditCard,
  Flame,
  HelpCircle,
  Info,
  MessageCircle,
  Play,
  TrendingUp,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import {
  ErrorBox,
  LoadingState,
  MasteryBadge,
  MasteryBar,
  SectionHeader,
  StatCard,
  masteryLevelFor,
  type MasteryLevel,
} from "@/components/ui"

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

type PracticeCandidate = {
  concept_id: string
  name: string
  reasoning: string
}

type PracticeRecs = { items: PracticeCandidate[]; fallback: PracticeCandidate | null }

export type ProjectTab = "tutor" | "quiz" | "flashcards" | "materials" | "structure" | "progress" | "overview"

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

function avg(values: (number | null)[]): number | null {
  const xs = values.filter((v): v is number => v !== null)
  if (xs.length === 0) return null
  return xs.reduce((s, v) => s + v, 0) / xs.length
}

export function Dashboard({
  projectId,
  overviewMode = false,
  onNavigate,
  onPracticeConcept,
}: {
  projectId: string
  overviewMode?: boolean
  onNavigate?: (tab: ProjectTab) => void
  onPracticeConcept?: (conceptId: string) => void
}) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState(false)
  const [streak, setStreak] = useState<number | null>(null)
  const [recs, setRecs] = useState<PracticeCandidate[]>([])

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

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ streak_days: number }>(`/projects/${projectId}/analytics`)
      .then((res) => {
        if (!cancelled) setStreak(res.data.streak_days)
      })
      .catch(() => {
        if (!cancelled) setStreak(null)
      })
    apiClient
      .get<PracticeRecs>(`/projects/${projectId}/practice/recommendations?limit=4`)
      .then((res) => {
        if (cancelled) return
        const list = [...res.data.items]
        if (res.data.fallback) list.push(res.data.fallback)
        setRecs(list.slice(0, 3))
      })
      .catch(() => {
        if (!cancelled) setRecs([])
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

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
  const flagged = data.concepts.filter((c) => c.mismatch)
  const underconfident = flagged.filter((c) => c.mismatch?.mismatch_type === "underconfident")
  const attention = flagged.filter((c) => c.mismatch?.mismatch_type !== "underconfident")

  const continueFrom = [...data.concepts]
    .filter((c) => c.last_evidence_at)
    .sort((a, b) => (b.last_evidence_at ?? "").localeCompare(a.last_evidence_at ?? ""))[0]

  const byTopic = new Map<string, ConceptProgress[]>()
  for (const c of data.concepts) {
    const list = byTopic.get(c.topic) ?? []
    list.push(c)
    byTopic.set(c.topic, list)
  }
  const topicRows = [...byTopic.entries()].map(([topic, list]) => ({
    topic,
    mcq: avg(list.map((c) => c.mcq)),
    applied: avg(list.map((c) => c.applied)),
  }))

  const go = (tab: ProjectTab) => onNavigate?.(tab)
  const practice = (conceptId: string) => {
    if (onPracticeConcept) onPracticeConcept(conceptId)
    else go("quiz")
  }

  return (
    <div className="space-y-10">
      <SectionHeader title="Dashboard" subtitle="Your learning health at a glance" />

      <div>
        <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Your Learning Health</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <StatCard label="Concepts Mastered" value={mastered} accent="green" icon={<Brain size={18} />} />
          <StatCard label="Developing" value={developing} accent="amber" icon={<TrendingUp size={18} />} />
          <StatCard label="Weak" value={weak} accent="red" icon={<AlertTriangle size={18} />} />
          <StatCard label="Mismatches" value={flagged.length} accent="amber" icon={<Info size={18} />} />
          <StatCard
            label="Study Streak"
            value={streak === null ? "—" : `${streak} day${streak === 1 ? "" : "s"}`}
            accent="indigo"
            icon={<Flame size={18} />}
          />
        </div>
      </div>

      {continueFrom && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-5 flex items-start justify-between">
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Continue Learning</div>
              <h2 className="text-xl font-semibold text-slate-900">{continueFrom.title}</h2>
              <div className="mt-2 flex items-center gap-3">
                <MasteryBadge level={toMasteryLevel(continueFrom.status, continueFrom.mcq)} />
                {continueFrom.last_evidence_at && (
                  <span className="text-xs text-slate-400">
                    Last practiced {new Date(continueFrom.last_evidence_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
            <div className="hidden flex-col gap-1 text-right text-xs sm:flex">
              <span className="font-mono-data text-green-600">
                MCQ {continueFrom.mcq === null ? "—" : `${Math.round(continueFrom.mcq)}%`}
              </span>
              <span className="font-mono-data text-amber-600">
                Applied {continueFrom.applied === null ? "—" : `${Math.round(continueFrom.applied)}%`}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => go("tutor")} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
              <Play size={14} /> Continue
            </button>
            <button type="button" onClick={() => go("tutor")} className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <MessageCircle size={14} /> Ask Tutor
            </button>
            <button type="button" onClick={() => practice(continueFrom.concept_id)} className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <HelpCircle size={14} /> Practice
            </button>
            <button type="button" onClick={() => go("flashcards")} className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <CreditCard size={14} /> Flashcards
            </button>
          </div>
        </div>
      )}

      {topicRows.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-4 text-sm font-semibold text-slate-700">MCQ Mastery by Topic</div>
            <div className="space-y-3.5">
              {topicRows.map((t) =>
                t.mcq === null ? null : (
                  <MasteryBar key={t.topic} value={Math.round(t.mcq)} level={masteryLevelFor(t.mcq)} label={t.topic} />
                ),
              )}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-4 text-sm font-semibold text-slate-700">Applied Mastery by Topic</div>
            <div className="space-y-3.5">
              {topicRows.map((t) =>
                t.applied === null ? null : (
                  <MasteryBar key={t.topic} value={Math.round(t.applied)} level={masteryLevelFor(t.applied)} label={t.topic} />
                ),
              )}
            </div>
          </div>
        </div>
      )}

      {(attention.length > 0 || underconfident.length > 0) && (
        <div>
          <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Concepts That Need Attention
          </div>
          <div className="space-y-3">
            {attention.slice(0, overviewMode ? 4 : 10).map((c) => (
              <div key={c.concept_id} className="rounded-xl border border-amber-100 bg-white p-5">
                <div className="flex items-start gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-50">
                    <AlertTriangle size={16} className="text-amber-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-800">{c.title}</span>
                      <span className="text-xs text-slate-400">·</span>
                      <span className="text-xs font-medium text-red-600">
                        {c.mcq === null ? "no recognition evidence" : `${Math.round(c.mcq)}% recognition`}
                      </span>
                      <span className="text-xs text-slate-400">·</span>
                      <span className="text-xs font-medium text-amber-600">
                        {c.mismatch ? mismatchLabel(c.mismatch.mismatch_type) : c.status}
                      </span>
                    </div>
                    {c.mismatch && <p className="text-xs text-slate-500">{c.mismatch.reason}</p>}
                    <div className="mt-1 text-xs text-slate-400">
                      {c.topic} → {c.subtopic}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => practice(c.concept_id)}
                    className="shrink-0 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
                  >
                    Study this
                  </button>
                </div>
              </div>
            ))}
            {underconfident.slice(0, 2).map((c) => (
              <div key={c.concept_id} className="rounded-xl border border-blue-100 bg-white p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-800">{c.title}</span>
                      <span className="text-xs font-medium text-green-600">
                        {c.mcq === null ? "no recognition evidence" : `${Math.round(c.mcq)}% correct`}
                      </span>
                      <span className="text-xs text-slate-400">·</span>
                      <span className="text-xs font-medium text-blue-600">Low confidence</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {c.mismatch?.reason ?? "You may understand this concept better than you think. Practice to calibrate your confidence."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => practice(c.concept_id)}
                    className="shrink-0 text-xs font-medium text-indigo-600 hover:underline"
                  >
                    Study →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Recommended Next</div>
        {rec ? (
          <div className="mb-4 rounded-xl bg-indigo-600 p-6 text-white">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-300">Primary Recommendation</div>
            <h3 className="mb-1 text-lg font-semibold">
              {actionLabel(rec.action_type)}: {rec.concept_name}
            </h3>
            <p className="mb-4 text-sm text-indigo-200">{rec.reasoning}</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => practice(rec.concept_id)}
                className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
              >
                Study this
              </button>
              <button
                type="button"
                onClick={() => void postAction("refresh")}
                disabled={acting}
                className="rounded-lg border border-indigo-400 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
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
          <div className="mb-4 rounded-xl border border-slate-200 bg-white p-6">
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
              <BarChart2 size={14} /> {acting ? "Working…" : "Generate recommendation"}
            </button>
          </div>
        )}
        {recs.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-3">
            {recs.map((r) => (
              <div key={r.concept_id} className="rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300">
                <div className="mb-0.5 text-xs text-slate-500">Practice</div>
                <div className="mb-2 text-sm font-semibold text-slate-800">{r.name}</div>
                <p className="mb-3 line-clamp-3 text-xs leading-relaxed text-slate-400">{r.reasoning}</p>
                <button
                  type="button"
                  onClick={() => practice(r.concept_id)}
                  className="text-xs font-medium text-indigo-600 hover:underline"
                >
                  Go →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
