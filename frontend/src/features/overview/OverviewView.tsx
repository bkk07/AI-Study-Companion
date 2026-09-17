import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, ChevronRight, Clock, CreditCard, Flame, HelpCircle, MessageCircle, Play, Sparkles, Target } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { ErrorBox, LoadingState, StatCard } from "@/components/ui"
import { Brain, FileText, BarChart2 } from "lucide-react"
import type { ProjectTab } from "@/features/dashboard/Dashboard"

type ConceptProgress = {
  concept_id: string
  title: string
  topic: string
  subtopic: string
  mcq: number | null
  applied: number | null
  final_mastery: number | null
  mcq_count: number
  applied_count: number
  last_evidence_at: string | null
  status: string
  mismatch: { mismatch_type: string; gap: number; reason: string } | null
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

type TimelinePoint = { date: string; label: string; mcq: number | null; applied: number | null }
type AnalyticsOverview = {
  tutor_interactions: number
  assessments_total: number
  flashcards_total: number
  timeline: TimelinePoint[]
  before_now: BeforeNow[]
}

function baseMastery(c: ConceptProgress): number | null {
  if (typeof c.final_mastery === "number") return c.final_mastery
  const vals = [c.mcq, c.applied].filter((v): v is number => v !== null)
  if (vals.length === 0) return null
  return vals.reduce((s, v) => s + v, 0) / vals.length
}

/** Recency-decayed mastery: stale evidence counts less toward readiness. */
function effectiveMastery(c: ConceptProgress, now: number): number {
  const base = baseMastery(c)
  if (base === null) return 0
  if (!c.last_evidence_at) return base
  const days = Math.max(0, (now - new Date(c.last_evidence_at).getTime()) / 86400000)
  if (days <= 14) return base
  if (days <= 30) return base * 0.85
  return base * 0.7
}

function heatClass(value: number | null): string {
  if (value === null) return "bg-slate-200 text-slate-500"
  if (value < 34) return "bg-red-400 text-white"
  if (value <= 66) return "bg-amber-400 text-white"
  if (value < 85) return "bg-sky-500 text-white"
  return "bg-green-500 text-white"
}

function ReadinessRing({ value }: { value: number }) {
  const r = 52
  const circ = 2 * Math.PI * r
  const filled = (Math.min(100, Math.max(0, value)) / 100) * circ
  return (
    <div className="relative h-32 w-32 shrink-0">
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#f1f5f9" strokeWidth="11" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke="#4f46e5" strokeWidth="11" strokeLinecap="round"
          strokeDasharray={`${filled} ${circ - filled}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono-data text-3xl font-bold text-slate-900">{Math.round(value)}%</span>
        <span className="text-[11px] font-medium text-slate-400">ready</span>
      </div>
    </div>
  )
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
  const [streak, setStreak] = useState<number | null>(null)
  const [dueCards, setDueCards] = useState(0)
  const [tutorCount, setTutorCount] = useState<number | null>(null)
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [planMinutes, setPlanMinutes] = useState(20)
  const [targetDate, setTargetDate] = useState(() => new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10))
  const [graph, setGraph] = useState<{ nodes: { id: string; title: string; topic: string; mastery: number | null; status: string }[]; edges: { from_id: string; to_id: string; relation: string }[] } | null>(null)

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
      .get<PracticeRecs>(`/projects/${projectId}/practice/recommendations?limit=4`)
      .then((res) => {
        if (cancelled) return
        const list = [...res.data.items]
        if (res.data.fallback) list.push(res.data.fallback)
        setRecs(list.slice(0, 4))
      })
      .catch(() => {
        if (!cancelled) setRecs([])
      })
    apiClient
      .get<{ materials_total: number; avg_final: number | null; quiz_attempts_completed: number; streak_days: number }>(
        `/projects/${projectId}/analytics`,
      )
      .then((res) => {
        if (cancelled) return
        setDocCount(res.data.materials_total)
        setQuizAttempts(res.data.quiz_attempts_completed)
        // Single definition of average mastery (Plan A weighted final),
        // matching Analytics and Dashboard — not a plain MCQ/Applied mean.
        setAvgMastery(res.data.avg_final !== null ? `${Math.round(res.data.avg_final)}%` : null)
        setStreak(res.data.streak_days)
      })
      .catch(() => {
        if (!cancelled) {
          setDocCount(null)
          setQuizAttempts(null)
          setAvgMastery(null)
          setStreak(null)
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
    apiClient
      .get<{ due_count: number }>(`/projects/${projectId}/flashcards?due_only=true&limit=1`)
      .then((res) => {
        if (!cancelled) setDueCards(res.data.due_count)
      })
      .catch(() => {
        if (!cancelled) setDueCards(0)
      })
    apiClient
      .get<AnalyticsOverview>(`/projects/${projectId}/analytics/overview`, { params: { time_range: "all" } })
      .then((res) => {
        if (cancelled) return
        setTutorCount(res.data.tutor_interactions)
        setTimeline(res.data.timeline)
      })
      .catch(() => {
        if (!cancelled) {
          setTutorCount(null)
          setTimeline([])
        }
      })
    apiClient
      .get<{ nodes: { id: string; title: string; topic: string; mastery: number | null; status: string }[]; edges: { from_id: string; to_id: string; relation: string }[] }>(
        `/projects/${projectId}/knowledge/graph`,
      )
      .then((res) => {
        if (!cancelled) setGraph(res.data)
      })
      .catch(() => {
        if (!cancelled) setGraph(null)
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

  const now = Date.now()
  const concepts = data.concepts
  const mastered = concepts.filter((c) => c.status === "Mastered" || c.status === "Strong").length
  const developing = concepts.filter((c) => c.status === "Developing").length
  const weak = concepts.filter((c) => c.status === "Needs Practice").length
  const mismatches = concepts.filter((c) => c.mismatch !== null).length

  // Readiness: mean recency-decayed mastery across practice targets.
  const readiness = concepts.length
    ? concepts.reduce((s, c) => s + effectiveMastery(c, now), 0) / concepts.length
    : 0

  // Weakest-first (ties fall back to curriculum order from the API).
  const weakestFirst = [...concepts].sort((a, b) => effectiveMastery(a, now) - effectiveMastery(b, now))
  const heroRec = recs[0] ?? null
  const heroConcept = weakestFirst[0] ?? null
  const heroId = heroRec?.concept_id ?? heroConcept?.concept_id ?? null
  const heroTitle = heroRec?.name ?? heroConcept?.title ?? "Nothing to study yet"
  const heroWhy = heroRec?.reasoning
    ?? (heroConcept ? `Weakest concept at ${Math.round(effectiveMastery(heroConcept, now))}% effective mastery — start here.` : "Upload material to build your knowledge map.")

  const continueFrom = [...concepts]
    .filter((c) => c.last_evidence_at)
    .sort((a, b) => (b.last_evidence_at ?? "").localeCompare(a.last_evidence_at ?? ""))[0]
  const resume = continueFrom && continueFrom.concept_id !== heroId ? continueFrom : null

  const byTopic = new Map<string, ConceptProgress[]>()
  for (const c of concepts) {
    const list = byTopic.get(c.topic) ?? []
    list.push(c)
    byTopic.set(c.topic, list)
  }
  const heatTopics = [...byTopic.entries()].map(([topic, list]) => {
    const vals = list.map((c) => effectiveMastery(c, now))
    const avgVal = list.length ? vals.reduce((s, v) => s + v, 0) / list.length : null
    const ready = list.filter((c) => c.status === "Mastered" || c.status === "Strong").length
    return { topic, total: list.length, ready, avg: list.length ? avgVal : null }
  })
  const weakestTopic = [...heatTopics].filter((t) => t.avg !== null).sort((a, b) => (a.avg ?? 0) - (b.avg ?? 0))[0] ?? null

  // Attention inbox: overconfident → recognition gaps → forgotten masters, max 3.
  type InboxItem = { key: string; eyebrow: string; title: string; body: string; conceptId: string; cta: string; run: () => void }
  const inbox: InboxItem[] = []
  for (const c of concepts.filter((x) => x.mismatch?.mismatch_type === "overconfident").slice(0, 3)) {
    inbox.push({
      key: `oc-${c.concept_id}`, eyebrow: "Calibrate confidence", title: c.title,
      body: c.mismatch?.reason ?? "High confidence, low accuracy — slow down and verify.",
      conceptId: c.concept_id, cta: "Quiz me",
      run: () => practice(c.concept_id),
    })
  }
  for (const c of concepts.filter((x) => x.mismatch?.mismatch_type === "mcq_high_applied_low").slice(0, 3)) {
    if (inbox.length >= 3 || inbox.some((i) => i.conceptId === c.concept_id)) continue
    inbox.push({
      key: `gap-${c.concept_id}`, eyebrow: "Apply it, don't just recognize it", title: c.title,
      body: c.mismatch?.reason ?? "Recognition outruns applied understanding — practice using it.",
      conceptId: c.concept_id, cta: "Explain back",
      run: () => go("open-ended"),
    })
  }
  const forgotten = concepts
    .filter((c) => (c.status === "Mastered" || c.status === "Strong") && c.last_evidence_at
      && (now - new Date(c.last_evidence_at).getTime()) / 86400000 > 14)
    .sort((a, b) => (a.last_evidence_at ?? "").localeCompare(b.last_evidence_at ?? ""))
  for (const c of forgotten) {
    if (inbox.length >= 3 || inbox.some((i) => i.conceptId === c.concept_id)) continue
    const days = Math.round((now - new Date(c.last_evidence_at as string).getTime()) / 86400000)
    inbox.push({
      key: `fade-${c.concept_id}`, eyebrow: "Fading — review before it slips", title: c.title,
      body: `Mastered but untouched for ${days} days. A quick review locks it back in.`,
      conceptId: c.concept_id, cta: "Review",
      run: () => practice(c.concept_id),
    })
  }

  // Momentum: active days in the last 7 timeline points + direction.
  const week = timeline.slice(-7)
  const trend = week.length >= 2 && week[0].mcq !== null && week[week.length - 1].mcq !== null
    ? (week[week.length - 1].mcq as number) - (week[0].mcq as number)
    : null

  // Readiness pace vs target date (linear projection, clearly labeled estimate).
  const needed = 85 - readiness
  const pacePerDay = trend !== null ? trend / 7 : null
  const targetDays = Math.max(0, Math.round((new Date(targetDate || Date.now()).getTime() - now) / 86400000))

  // Session planner mix from the hero concept + due cards.
  const planMcq = Math.max(3, Math.round(planMinutes / 2.5))
  const planCards = Math.min(dueCards, planMinutes >= 20 ? 8 : 5)
  const planExplain = planMinutes >= 20 ? 1 : 0

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Overview</h1>
        <p className="mt-0.5 text-sm text-slate-500">Your next session, planned for you</p>
      </div>

      {/* NEXT UP — the one action that matters */}
      <div className="rounded-2xl bg-indigo-600 p-6 text-white sm:p-7">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-indigo-300">
          <Sparkles size={12} /> Next up · about 15 min
        </p>
        <h2 className="mt-1.5 text-xl font-semibold">{heroTitle}</h2>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-indigo-200">{heroWhy}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!heroId}
            onClick={() => heroId && practice(heroId)}
            className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
          >
            <Play size={14} /> Start quiz
          </button>
          {dueCards > 0 && (
            <button
              type="button"
              onClick={() => go("flashcards")}
              className="flex items-center gap-2 rounded-lg border border-indigo-400 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
            >
              <CreditCard size={14} /> {dueCards} due cards
            </button>
          )}
          <button
            type="button"
            onClick={() => go("tutor")}
            className="flex items-center gap-2 rounded-lg border border-indigo-400 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            <MessageCircle size={14} /> Ask tutor
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-indigo-200">
          {resume && (
            <button type="button" onClick={() => practice(resume.concept_id)} className="hover:text-white hover:underline">
              Resume: {resume.title}
            </button>
          )}
          {recs.slice(1, 3).map((r) => (
            <button key={r.concept_id} type="button" onClick={() => practice(r.concept_id)} className="hover:text-white hover:underline">
              Later: {r.name}
            </button>
          ))}
        </div>
      </div>

      {/* ATTENTION INBOX — max 3 decisions */}
      {inbox.length > 0 ? (
        <div>
          <div className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <AlertTriangle size={12} /> Needs your attention
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {inbox.map((item) => (
              <div key={item.key} className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-700">{item.eyebrow}</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">{item.title}</div>
                <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">{item.body}</p>
                <button
                  type="button"
                  onClick={item.run}
                  className="mt-2.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
                >
                  {item.cta} →
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        concepts.length > 0 && (
          <div className="rounded-xl border border-green-100 bg-green-50/60 px-5 py-3.5 text-sm text-green-800">
            All clear — no calibration risks, gaps, or fading masters right now.
          </div>
        )
      )}

      {/* READINESS + MOMENTUM */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex items-center gap-5 rounded-xl border border-slate-200 bg-white p-6">
          <ReadinessRing value={readiness} />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <Target size={12} /> Exam readiness
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
              <strong className="text-slate-900">{mastered}/{concepts.length}</strong> concepts exam-ready
              {weakestTopic && (
                <> · focus <strong className="text-slate-900">{weakestTopic.topic}</strong> ({Math.round(weakestTopic.avg ?? 0)}%)</>
              )}
            </p>
            <p className="mt-1 text-xs text-slate-400">Decays with stale practice — recent evidence counts most.</p>
            <div className="mt-2 flex gap-3 text-xs">
              <span className="text-green-700">{mastered} ready</span>
              <span className="text-amber-700">{developing} building</span>
              <span className="text-red-600">{weak} weak</span>
              {mismatches > 0 && <span className="text-orange-600">{mismatches} mismatched</span>}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-xs">
              <label htmlFor="cockpit-target" className="font-medium text-slate-500">Exam date</label>
              <input
                id="cockpit-target"
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-700"
              />
              <span className="text-slate-500">
                {needed <= 0
                  ? "Exam-ready — maintain with weekly reviews."
                  : pacePerDay === null
                    ? `${Math.round(needed)} pts to 85 — study a few days to gauge your pace.`
                    : pacePerDay <= 0
                      ? `${Math.round(needed)} pts to 85 in ${targetDays}d — pace stalled, a review sprint will restart it.`
                      : (() => {
                          const etaDays = Math.ceil(needed / pacePerDay)
                          const eta = new Date(now + etaDays * 86400000).toLocaleDateString()
                          return etaDays <= targetDays
                            ? `On track — 85 around ${eta} at +${pacePerDay.toFixed(1)}/day (est.).`
                            : `Behind — need +${(needed / Math.max(1, targetDays)).toFixed(1)}/day, running at +${pacePerDay.toFixed(1)}/day.`;
                        })()}
              </span>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Flame size={12} /> Momentum
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Streak", value: streak !== null ? `${streak}d` : "—" },
              { label: "Active days", value: `${week.length}/7` },
              { label: "Quizzes", value: quizAttempts !== null ? `${quizAttempts}` : "—" },
              { label: "Tutor Q&A", value: tutorCount !== null ? `${tutorCount}` : "—" },
            ].map((s) => (
              <div key={s.label} className="rounded-lg bg-slate-50 px-3 py-2.5 text-center">
                <div className="font-mono-data text-lg font-bold text-slate-900">{s.value}</div>
                <div className="mt-0.5 text-[11px] text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">
            {trend === null
              ? "Study a few days to reveal your trend."
              : trend >= 0
                ? `Trending up +${Math.round(trend)}% MCQ this week — keep going.`
                : `Dipped ${Math.round(trend)}% MCQ this week — a short review session will recover it.`}
          </p>
        </div>
      </div>

      {/* SESSION PLANNER */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <Clock size={12} /> Session planner
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {[10, 20, 30].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setPlanMinutes(m)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${planMinutes === m ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
            >
              {m} min
            </button>
          ))}
          <span className="ml-1 text-sm text-slate-600">
            {planMcq} adaptive questions{planCards > 0 ? ` + ${planCards} flashcards` : ""}{planExplain > 0 ? " + 1 explain-back" : ""}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!heroId}
            onClick={() => heroId && practice(heroId)}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <HelpCircle size={14} /> Start {planMcq} questions
          </button>
          {planCards > 0 && (
            <button
              type="button"
              onClick={() => go("flashcards")}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <CreditCard size={14} /> Review cards
            </button>
          )}
          {planExplain > 0 && (
            <button
              type="button"
              onClick={() => go("open-ended")}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <MessageCircle size={14} /> Explain back
            </button>
          )}
        </div>
      </div>

      {/* MASTERY HEATMAP */}
      {heatTopics.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Mastery heatmap</div>
            <button type="button" onClick={() => go("structure")} className="flex items-center gap-1 text-sm text-indigo-600 hover:underline">
              View full map <ChevronRight size={14} />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {heatTopics.map((t) => (
              <button
                key={t.topic}
                type="button"
                onClick={() => go("structure")}
                title={`${t.topic} · ${t.ready}/${t.total} exam-ready`}
                style={{ flexGrow: t.total, flexBasis: 120 }}
                className={`min-w-[120px] rounded-lg px-3 py-3 text-left transition-transform hover:scale-[1.02] ${heatClass(t.avg)}`}
              >
                <div className="truncate text-sm font-semibold">{t.topic}</div>
                <div className="mt-0.5 text-xs opacity-80">{t.avg === null ? "not started" : `${Math.round(t.avg)}% · ${t.ready}/${t.total}`}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* KNOWLEDGE GRAPH MINI-MAP */}
      {graph && graph.nodes.length > 0 && (() => {
        const laneH = 40
        const labelW = 176
        const gapX = 30
        const pos = new Map<string, { x: number; y: number }>()
        const lanes: { topic: string; ids: string[] }[] = []
        const byTopicG = new Map<string, string[]>()
        for (const n of graph.nodes) {
          const list = byTopicG.get(n.topic) ?? []
          list.push(n.id)
          byTopicG.set(n.topic, list)
        }
        let li = 0
        for (const [topic, ids] of byTopicG) {
          ids.forEach((id, i) => pos.set(id, { x: labelW + 26 + i * gapX, y: li * laneH + laneH / 2 }))
          lanes.push({ topic, ids })
          li += 1
        }
        const maxX = Math.max(...[...pos.values()].map((p) => p.x), 100) + 36
        const height = lanes.length * laneH + 12
        const shortTopic = (t: string) => {
          const stripped = t.replace(/^\d+\.\s*/, "")
          return stripped.length > 24 ? `${stripped.slice(0, 23)}…` : stripped
        }
        const dotClass = (status: string) =>
          status === "Mastered" ? "#22c55e" : status === "Strong" ? "#0ea5e9"
          : status === "Developing" ? "#f59e0b" : status === "Needs Practice" ? "#ef4444" : "#cbd5e1"
        const shownEdges = graph.edges.filter((e) => pos.has(e.from_id) && pos.has(e.to_id)).slice(0, 200)
        return (
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-1 flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Knowledge graph · {graph.nodes.length} concepts · {graph.edges.length} links
              </div>
              <button type="button" onClick={() => go("structure")} className="flex items-center gap-1 text-sm text-indigo-600 hover:underline">
                View full map <ChevronRight size={14} />
              </button>
            </div>
            <p className="mb-3 text-xs text-slate-400">Solid lines = prerequisites · dotted = related · click a dot to study it</p>
            <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
              {[
                ["Mastered", "#22c55e"], ["Strong", "#0ea5e9"], ["Developing", "#f59e0b"],
                ["Needs practice", "#ef4444"], ["Not started", "#cbd5e1"],
              ].map(([label, color]) => (
                <span key={label} className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
                  {label}
                </span>
              ))}
            </div>
            <div className="max-h-[460px] overflow-auto rounded-lg border border-slate-100 bg-slate-50/50 p-2">
            <svg viewBox={`0 0 ${maxX} ${height}`} width={maxX} height={height} className="block">
              {shownEdges.map((e, i) => {
                const a = pos.get(e.from_id)
                const b = pos.get(e.to_id)
                if (!a || !b) return null
                const my = (a.y + b.y) / 2
                return (
                  <path
                    key={i}
                    d={`M ${a.x} ${a.y} C ${a.x} ${my}, ${b.x} ${my}, ${b.x} ${b.y}`}
                    fill="none"
                    stroke={e.relation === "PREREQUISITE_OF" ? "#818cf8" : "#cbd5e1"}
                    strokeWidth={e.relation === "PREREQUISITE_OF" ? 1.6 : 1}
                    opacity={e.relation === "PREREQUISITE_OF" ? 0.7 : 0.3}
                  />
                )
              })}
              {lanes.map((lane, idx) => (
                <text key={lane.topic} x={6} y={idx * laneH + laneH / 2 + 4} fontSize="11" fontWeight={500} fill="#475569">
                  {`${shortTopic(lane.topic)} (${lane.ids.length})`}
                </text>
              ))}
              {graph.nodes.map((n) => {
                const p = pos.get(n.id)
                if (!p) return null
                return (
                  <g key={n.id} onClick={() => practice(n.id)} style={{ cursor: "pointer" }}>
                    <title>{`${n.title} · ${n.status}${n.mastery !== null ? ` · ${Math.round(n.mastery)}%` : ""}`}</title>
                    <circle cx={p.x} cy={p.y} r={9} fill={dotClass(n.status)} stroke="#ffffff" strokeWidth={2} opacity={0.95} />
                  </g>
                )
              })}
            </svg>
            </div>
          </div>
        )
      })()}

      {/* COMPACT STATS */}
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
          sub="Overall"
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

      {recs.length > 0 && (
        <div>
          <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Why these picks?</div>
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

      {concepts.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center">
          <p className="font-semibold text-slate-800">Mastery will appear here</p>
          <p className="mt-1 text-sm text-slate-500">
            Upload material and wait for processing, then answer a quiz or explain a concept.
          </p>
        </div>
      )}
    </div>
  )
}

