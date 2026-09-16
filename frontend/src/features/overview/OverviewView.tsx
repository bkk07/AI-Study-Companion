import { useCallback, useEffect, useState } from "react"
import { ChevronRight, CreditCard, HelpCircle, MessageCircle, Play } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { ErrorBox, LoadingState, MasteryBadge, StatCard } from "@/components/ui"
import { Brain, FileText, BarChart2 } from "lucide-react"
import type { ProjectTab } from "@/features/dashboard/Dashboard"

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
}

type DashboardData = {
  concepts: ConceptProgress[]
  recommendation: null | { id: string }
}

type PracticeCandidate = {
  concept_id: string
  name: string
  reasoning: string
}

type PracticeRecs = { items: PracticeCandidate[]; fallback: PracticeCandidate | null }

function statusLevel(status: string): "mastered" | "developing" | "weak" | "unassessed" {
  if (status === "Mastered" || status === "Strong") return "mastered"
  if (status === "Developing") return "developing"
  if (status === "Needs Practice") return "weak"
  return "unassessed"
}

export function OverviewView({
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
  const [recs, setRecs] = useState<PracticeCandidate[]>([])
  const [docCount, setDocCount] = useState<number | null>(null)
  const [avgMastery, setAvgMastery] = useState<string | null>(null)
  const [quizAttempts, setQuizAttempts] = useState<number | null>(null)
  const [cardReviews, setCardReviews] = useState<number | null>(null)

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
      .get<PracticeRecs>(`/projects/${projectId}/practice/recommendations?limit=3`)
      .then((res) => {
        if (cancelled) return
        const list = [...res.data.items]
        if (res.data.fallback) list.push(res.data.fallback)
        setRecs(list.slice(0, 3))
      })
      .catch(() => {
        if (!cancelled) setRecs([])
      })
    apiClient
      .get<{ materials_total: number; avg_mcq: number | null; avg_applied: number | null; quiz_attempts_completed: number }>(
        `/projects/${projectId}/analytics`,
      )
      .then((res) => {
        if (cancelled) return
        setDocCount(res.data.materials_total)
        setQuizAttempts(res.data.quiz_attempts_completed)
        const vals = [res.data.avg_mcq, res.data.avg_applied].filter((v): v is number => v !== null)
        setAvgMastery(vals.length ? `${Math.round(vals.reduce((s, v) => s + v, 0) / vals.length)}%` : null)
      })
      .catch(() => {
        if (!cancelled) {
          setDocCount(null)
          setQuizAttempts(null)
          setAvgMastery(null)
        }
      })
    apiClient
      .get<{ cards: { total_reviews: number }[] }>(`/projects/${projectId}/flashcards?limit=100`)
      .then((res) => {
        if (!cancelled) setCardReviews(res.data.cards.reduce((s, c) => s + c.total_reviews, 0))
      })
      .catch(() => {
        if (!cancelled) setCardReviews(null)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  if (loading) return <LoadingState text="Loading progress…" />
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />
  if (!data) return null

  const go = (tab: ProjectTab) => onNavigate?.(tab)
  const practice = (conceptId: string) => {
    if (onPracticeConcept) onPracticeConcept(conceptId)
    else go("quiz")
  }

  const concepts = data.concepts
  const mastered = concepts.filter((c) => c.status === "Mastered" || c.status === "Strong").length
  const developing = concepts.filter((c) => c.status === "Developing").length
  const weak = concepts.filter((c) => c.status === "Needs Practice").length
  const mismatches = concepts.filter(
    (c) =>
      c.mcq !== null &&
      c.applied !== null &&
      (c.mcq - c.applied > 20 || (c.mcq >= 70 && c.applied < 55)),
  ).length

  const continueFrom = [...concepts]
    .filter((c) => c.last_evidence_at)
    .sort((a, b) => (b.last_evidence_at ?? "").localeCompare(a.last_evidence_at ?? ""))[0]

  const byTopic = new Map<string, ConceptProgress[]>()
  for (const c of concepts) {
    const list = byTopic.get(c.topic) ?? []
    list.push(c)
    byTopic.set(c.topic, list)
  }
  const topicRows = [...byTopic.entries()].map(([topic, list]) => ({
    topic,
    subtopics: new Set(list.map((c) => c.subtopic)).size,
    total: list.length,
    mastered: list.filter((c) => c.status === "Mastered" || c.status === "Strong").length,
  }))

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Overview</h1>
        <p className="mt-0.5 text-sm text-slate-500">Your personal learning workspace</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Documents" value={docCount ?? "—"} icon={<FileText size={18} />} accent="slate" />
        <StatCard label="Concepts" value={concepts.length} icon={<Brain size={18} />} accent="indigo" />
        <StatCard
          label="Quiz Attempts"
          value={quizAttempts ?? "—"}
          icon={<HelpCircle size={18} />}
          accent="slate"
        />
        <StatCard
          label="Flashcards Reviewed"
          value={cardReviews ?? "—"}
          icon={<CreditCard size={18} />}
          accent="slate"
        />
        <StatCard
          label="Avg Mastery"
          value={avgMastery ?? "—"}
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

      {continueFrom ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-5 flex items-start justify-between">
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Continue Learning</div>
              <h2 className="text-xl font-semibold text-slate-900">{continueFrom.title}</h2>
              <div className="mt-2 flex items-center gap-3">
                <MasteryBadge level={statusLevel(continueFrom.status)} />
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
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center">
          <p className="font-semibold text-slate-800">Mastery will appear here</p>
          <p className="mt-1 text-sm text-slate-500">
            Upload material and wait for processing, then answer a quiz or explain a concept.
          </p>
        </div>
      )}

      {topicRows.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Your Learning Map</div>
              <h2 className="text-base font-semibold text-slate-900">Topics → Subtopics → Concepts</h2>
            </div>
            <button type="button" onClick={() => go("structure")} className="flex items-center gap-1 text-sm text-indigo-600 hover:underline">
              View full map <ChevronRight size={14} />
            </button>
          </div>
          <div className="space-y-3">
            {topicRows.map((t) => (
              <div key={t.topic} className="flex items-center gap-4 border-b border-slate-50 py-2 last:border-0">
                <div className={`h-2 w-2 shrink-0 rounded-full ${t.mastered === t.total && t.total > 0 ? "bg-green-500" : t.mastered > 0 ? "bg-amber-400" : "bg-slate-300"}`} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-slate-800">{t.topic}</div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    {t.subtopics} subtopics · {t.total} concepts
                  </div>
                </div>
                <div className="font-mono-data text-xs text-slate-500">{t.mastered}/{t.total} mastered</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {recs.length > 0 && (
        <div>
          <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Today&apos;s Recommended Plan</div>
          <div className="space-y-3">
            {recs.map((r) => (
              <div key={r.concept_id} className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-5">
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-slate-800">{r.name}</div>
                    <div className="mt-2 flex items-start gap-1">
                      <span className="shrink-0 text-xs font-medium text-slate-500">Why?</span>
                      <p className="text-xs leading-relaxed text-slate-500">{r.reasoning}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => practice(r.concept_id)}
                    className="shrink-0 text-xs font-medium text-indigo-600 hover:underline"
                  >
                    Study
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
