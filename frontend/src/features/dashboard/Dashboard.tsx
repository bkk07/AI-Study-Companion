import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AlertTriangle,
  Brain,
  Flame,
  Info,
  TrendingUp,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import {
  ErrorBox,
  LoadingState,
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
  avg_confidence: number | null
  accuracy: number | null
  evaluated_count: number
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

type FlashCard = { id: string; concept_id: string }

type PracticeCandidate = { concept_id: string; name: string; reasoning: string }
type PracticeRecs = { items: PracticeCandidate[]; fallback: PracticeCandidate | null }

type TopicNode = {
  id: string
  title: string
  subtopics: { id: string; title: string; concepts: { id: string; title: string }[] }[]
}

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

function confidenceWord(avg: number | null, fallbackType?: string): string {
  if (avg !== null) {
    if (avg >= 4) return "High confidence"
    if (avg <= 2) return "Low confidence"
    return "Medium confidence"
  }
  if (fallbackType === "overconfident") return "High confidence"
  if (fallbackType === "underconfident") return "Low confidence"
  return "Confidence gap"
}

function avg(values: (number | null)[]): number | null {
  const xs = values.filter((v): v is number => v !== null)
  if (xs.length === 0) return null
  return xs.reduce((s, v) => s + v, 0) / xs.length
}

export function Dashboard({
  projectId,
  onNavigate,
  onPracticeConcept,
}: {
  projectId: string
  onNavigate?: (tab: ProjectTab) => void
  onPracticeConcept?: (conceptId: string) => void
}) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState(false)
  const [streak, setStreak] = useState<number | null>(null)
  const [dueCards, setDueCards] = useState<FlashCard[]>([])
  const [dueTotal, setDueTotal] = useState(0)
  const [recs, setRecs] = useState<PracticeCandidate[]>([])
  const [conceptMeta, setConceptMeta] = useState<Map<string, { title: string; topic: string }>>(new Map())

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
        setRecs(list)
      })
      .catch(() => {
        if (!cancelled) setRecs([])
      })
    apiClient
      .get<{ cards: FlashCard[]; due_count: number }>(`/projects/${projectId}/flashcards?due_only=true&limit=100`)
      .then((res) => {
        if (cancelled) return
        setDueCards(res.data.cards)
        setDueTotal(res.data.due_count)
      })
      .catch(() => {
        if (!cancelled) {
          setDueCards([])
          setDueTotal(0)
        }
      })
    apiClient
      .get<{ topics: TopicNode[] }>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (cancelled) return
        const map = new Map<string, { title: string; topic: string }>()
        for (const t of res.data.topics) {
          for (const s of t.subtopics) {
            for (const c of s.concepts) map.set(c.id, { title: c.title, topic: t.title })
          }
        }
        setConceptMeta(map)
      })
      .catch(() => {
        if (!cancelled) setConceptMeta(new Map())
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

  const dueByConcept = useMemo(() => {
    const counts = new Map<string, number>()
    for (const c of dueCards) counts.set(c.concept_id, (counts.get(c.concept_id) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [dueCards])

  const dueTopics = useMemo(() => {
    const topics = new Map<string, number>()
    for (const c of dueCards) {
      const topic = conceptMeta.get(c.concept_id)?.topic ?? "Other"
      topics.set(topic, (topics.get(topic) ?? 0) + 1)
    }
    return [...topics.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t)
  }, [dueCards, conceptMeta])

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

  const evidenced = data.concepts.filter((c) => c.applied !== null || c.mcq !== null)
  const lowestApplied = [...evidenced]
    .filter((c) => c.applied !== null)
    .sort((a, b) => (a.applied ?? 0) - (b.applied ?? 0))[0]
  const unassessed = data.concepts.find((c) => c.mcq === null && c.applied === null)
  const [topDueConceptId, topDueCount] = dueByConcept[0] ?? [null, 0]
  const topDueTitle = topDueConceptId ? (conceptMeta.get(topDueConceptId)?.title ?? "Flashcards") : null

  type Secondary = { key: string; eyebrow: string; title: string; body: string; run: () => void }
  const secondaries: Secondary[] = []
  const featured = new Set<string>()
  if (topDueConceptId && topDueTitle) {
    featured.add(topDueConceptId)
    secondaries.push({
      key: `due-${topDueConceptId}`,
      eyebrow: "Review flashcards",
      title: topDueTitle,
      body: `${topDueCount} flashcard${topDueCount === 1 ? " is" : "s are"} overdue based on spaced repetition schedule.`,
      run: () => go("flashcards"),
    })
  }
  if (unassessed) {
    featured.add(unassessed.concept_id)
    secondaries.push({
      key: `new-${unassessed.concept_id}`,
      eyebrow: "Practice",
      title: unassessed.title,
      body: "Not yet assessed. Understanding this concept requires applying it — not just recognizing it.",
      run: () => practice(unassessed.concept_id),
    })
  }
  if (dueTotal > 0) {
    secondaries.push({
      key: "due-all",
      eyebrow: "Review",
      title: `${dueTotal} due flashcard${dueTotal === 1 ? "" : "s"}`,
      body:
        dueTopics.length > 0
          ? `Cards are due across ${dueTopics.slice(0, 2).join(" and ")} topics.`
          : "Cards are due for review based on spaced repetition.",
      run: () => go("flashcards"),
    })
  }
  for (const r of recs) {
    if (secondaries.length >= 3 || featured.has(r.concept_id)) continue
    featured.add(r.concept_id)
    secondaries.push({
      key: `rec-${r.concept_id}`,
      eyebrow: "Practice",
      title: r.name,
      body: r.reasoning,
      run: () => practice(r.concept_id),
    })
  }

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
            value={typeof streak !== "number" ? "—" : `${streak} day${streak === 1 ? "" : "s"}`}
            accent="indigo"
            icon={<Flame size={18} />}
          />
        </div>
      </div>

      {topicRows.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-4 text-sm font-semibold text-slate-700">MCQ Mastery by Topic</div>
            <div className="space-y-3.5">
              {topicRows.map((t) =>
                t.mcq === null ? null : (
                  <MasteryBar key={t.topic} value={Math.round(t.mcq)} level={toMasteryLevel("", t.mcq)} label={t.topic} />
                ),
              )}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-4 text-sm font-semibold text-slate-700">Applied Mastery by Topic</div>
            <div className="space-y-3.5">
              {topicRows.map((t) =>
                t.applied === null ? null : (
                  <MasteryBar key={t.topic} value={Math.round(t.applied)} level={toMasteryLevel("", t.applied)} label={t.topic} />
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
            {attention.slice(0, 10).map((c) => {
              const rated = c.evaluated_count > 0 && c.accuracy !== null
              const pct = rated ? Math.round((c.accuracy ?? 0) * 100) : c.mcq === null ? null : Math.round(c.mcq)
              const conf = confidenceWord(c.avg_confidence, c.mismatch?.mismatch_type)
              return (
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
                        {pct === null ? "no correctness evidence" : `${pct}% ${rated ? "correct" : "recognition"}`}
                      </span>
                      <span className="text-xs text-slate-400">·</span>
                      <span className="text-xs font-medium text-amber-600">{conf.toLowerCase()}</span>
                    </div>
                    {c.mismatch && <p className="mb-2 text-xs text-slate-500">{c.mismatch.reason}</p>}
                    <div className="text-xs text-slate-400">
                      {rated
                        ? `Last ${c.evaluated_count} attempt${c.evaluated_count === 1 ? "" : "s"} · ${conf}, ${(c.accuracy ?? 0) >= 0.7 ? "high" : "low"} correctness`
                        : `${c.mcq_count + c.applied_count} evidence · ${c.mismatch ? mismatchLabel(c.mismatch.mismatch_type) : c.status}`}
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
              )
            })}
            {underconfident.slice(0, 2).map((c) => {
              const rated = c.evaluated_count > 0 && c.accuracy !== null
              const pct = rated ? Math.round((c.accuracy ?? 0) * 100) : c.mcq === null ? null : Math.round(c.mcq)
              return (
              <div key={c.concept_id} className="rounded-xl border border-blue-100 bg-white p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-800">{c.title}</span>
                      <span className="text-xs font-medium text-green-600">
                        {pct === null ? "no correctness evidence" : `${pct}% ${rated ? "correct" : "recognition"}`}
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
              )
            })}
          </div>
        </div>
      )}

      <div>
        <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Recommended Next</div>
        {lowestApplied ? (
          <div className="mb-4 rounded-xl bg-indigo-600 p-6 text-white">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-300">Primary Recommendation</div>
            <h3 className="mb-1 text-lg font-semibold">Practice {lowestApplied.title}</h3>
            <p className="mb-4 text-sm text-indigo-200">
              Your applied mastery ({Math.round(lowestApplied.applied ?? 0)}%) is the lowest among recently practiced topics.
            </p>
            <button
              type="button"
              onClick={() => practice(lowestApplied.concept_id)}
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
            >
              Study this
            </button>
          </div>
        ) : rec ? (
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
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {acting ? "Working…" : "Generate recommendation"}
            </button>
          </div>
        )}
        {secondaries.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-3">
            {secondaries.slice(0, 3).map((s) => (
              <div key={s.key} className="rounded-xl border border-slate-200 bg-white p-4 hover:border-slate-300">
                <div className="mb-0.5 text-xs text-slate-500">{s.eyebrow}</div>
                <div className="mb-2 text-sm font-semibold text-slate-800">{s.title}</div>
                <p className="mb-3 line-clamp-3 text-xs leading-relaxed text-slate-400">{s.body}</p>
                <button type="button" onClick={s.run} className="text-xs font-medium text-indigo-600 hover:underline">
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
