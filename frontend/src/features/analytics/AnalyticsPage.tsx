import { useCallback, useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  Brain,
  ClipboardCheck,
  CreditCard,
  FileText,
  HelpCircle,
  MessageCircle,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, SectionHeader, StatCard } from "@/components/ui"
import { GrowthView } from "@/features/analytics/GrowthView"

type TopicMastery = { topic: string; mcq: number | null; applied: number | null }
type ConfidencePoint = {
  concept_id: string
  concept: string
  confidence: number | null
  correctness: number | null
  attempts: number
  mismatch_type: string | null
}

type TimelinePoint = { date: string; label: string; mcq: number | null; applied: number | null }
type BeforeNow = {
  concept_id: string
  concept: string
  early_mcq: number | null
  early_applied: number | null
  current_mcq: number | null
  current_applied: number | null
}

type Overview = {
  materials_total: number
  concepts_count: number
  core_concepts_count: number
  topics_count: number
  quiz_attempts: number
  quiz_attempts_completed: number
  flashcards_total: number
  tutor_interactions: number
  assessments_total: number
  avg_mcq: number | null
  avg_applied: number | null
  evidenced_concepts: number
  streak_days: number
  topic_mastery: TopicMastery[]
  confidence_points: ConfidencePoint[]
  timeline: TimelinePoint[]
  before_now: BeforeNow[]
}

type Range = "2w" | "1m" | "all"

function round1(v: number | null): number | null {
  return v === null ? null : Math.round(v * 10) / 10
}

function fmtPct(v: number | null): string {
  return v === null ? "—" : `${Math.round(v)}%`
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-medium text-slate-700">{label}</div>
      {payload.map((p: { name: string; value: number | null; color?: string }) => (
        <div key={p.name} className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-slate-500">{p.name}:</span>
          <span className="font-semibold text-slate-800">
            {p.value === null || p.value === undefined ? "—" : `${Math.round(p.value)}%`}
          </span>
        </div>
      ))}
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ScatterTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload as
    | { concept: string; confidence: number; correctness: number; attempts: number }
    | undefined
  if (!d) return null
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-semibold text-slate-800">{d.concept}</div>
      <div className="text-slate-600">Confidence: {Math.round(d.confidence)}%</div>
      <div className="text-slate-600">Correctness: {Math.round(d.correctness)}%</div>
      <div className="mt-0.5 text-slate-400">{d.attempts} evaluated answers</div>
    </div>
  )
}

function shortName(concept: string): string {
  const initials = concept
    .split(/\s+/)
    .map((w) => w[0] ?? "")
    .join("")
    .slice(0, 4)
    .toUpperCase()
  return initials || concept.slice(0, 4).toUpperCase()
}

type DashConcept = {
  concept_id: string
  title: string
  topic: string
  mcq: number | null
  applied: number | null
  final_mastery?: number | null
  mcq_count: number
  applied_count: number
  last_evidence_at: string | null
  status: string
  mismatch: { mismatch_type: string; gap: number; reason: string } | null
  streams?: Record<string, { value: number | null; count: number }>
}

type LabTab = "overview" | "calibration" | "forgetting" | "effort" | "growth"

const LAB_TABS: { id: LabTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "calibration", label: "Calibration" },
  { id: "forgetting", label: "Forgetting" },
  { id: "effort", label: "Effort" },
  { id: "growth", label: "Growth" },
]

export function AnalyticsPage({ projectId, onNavigate, onPracticeConcept }: {
  projectId: string
  onNavigate?: (tab: "quiz" | "flashcards" | "practice" | "open-ended" | "tutor" | "structure") => void
  onPracticeConcept?: (conceptId: string) => void
}) {
  const [range, setRange] = useState<Range>("all")
  const [tab, setTab] = useState<LabTab>("overview")
  const [data, setData] = useState<Overview | null>(null)
  const [dash, setDash] = useState<DashConcept[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<Overview>(`/projects/${projectId}/analytics/overview`, {
        params: { time_range: range },
      })
      setData(res.data)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 404) setError("Project not found for this view.")
      else setError(detail ?? "Failed to load analytics.")
    } finally {
      setLoading(false)
    }
  }, [projectId, range])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ concepts: DashConcept[] }>(`/projects/${projectId}/dashboard`)
      .then((res) => {
        if (!cancelled) setDash(res.data.concepts)
      })
      .catch(() => {
        if (!cancelled) setDash([])
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  if (loading) return <LoadingState text="Loading analytics…" />
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />
  if (!data) return null

  const timeline = data.timeline.map((t) => ({
    ...t,
    mcq: round1(t.mcq),
    applied: round1(t.applied),
    date: t.label,
  }))
  const topics = data.topic_mastery.map((t) => ({
    topic: t.topic.length > 10 ? `${t.topic.slice(0, 9)}…` : t.topic,
    fullTopic: t.topic,
    mcq: round1(t.mcq),
    applied: round1(t.applied),
  }))
  const scatter = data.confidence_points
    .filter((p) => p.confidence !== null && p.correctness !== null)
    .map((p) => ({
      concept_id: p.concept_id,
      concept: p.concept,
      name: shortName(p.concept),
      confidence: Math.round(p.confidence as number),
      correctness: Math.round(p.correctness as number),
      attempts: p.attempts,
      mismatch_type: p.mismatch_type,
    }))

  const hasEvidence = data.evidenced_concepts > 0

  const practice = (conceptId: string) => {
    if (onPracticeConcept) onPracticeConcept(conceptId)
    else onNavigate?.("quiz")
  }

  function dashValue(c: DashConcept): number | null {
    if (typeof c.final_mastery === "number") return c.final_mastery
    const vals = [c.mcq, c.applied].filter((v): v is number => v !== null)
    if (vals.length === 0) return null
    return vals.reduce((s, v) => s + v, 0) / vals.length
  }

  // Distribution histogram across mastery bands (averages lie — shapes don't).
  const distBands = [
    { label: "Not started", color: "bg-slate-300", count: 0 },
    { label: "Weak", color: "bg-red-400", count: 0 },
    { label: "Developing", color: "bg-amber-400", count: 0 },
    { label: "Strong", color: "bg-sky-500", count: 0 },
    { label: "Mastered", color: "bg-green-500", count: 0 },
  ]
  for (const c of dash) {
    const v = dashValue(c)
    const band = v === null ? 0 : v < 34 ? 1 : v <= 66 ? 2 : v < 85 ? 3 : 4
    distBands[band].count += 1
  }
  const distMax = Math.max(1, ...distBands.map((b) => b.count))

  // Fading soon: solid mastery, untouched for 14+ days — review before it slips.
  const fading = dash
    .filter((c) => {
      const v = dashValue(c)
      if (v === null || v < 66 || !c.last_evidence_at) return false
      return (Date.now() - new Date(c.last_evidence_at).getTime()) / 86400000 > 14
    })
    .map((c) => ({
      ...c,
      days: Math.round((Date.now() - new Date(c.last_evidence_at as string).getTime()) / 86400000),
    }))
    .sort((a, b) => b.days - a.days)
    .slice(0, 6)

  // Effort vs outcome: evidence volume per stream + project-level verdict.
  const streamTotals: Record<string, number> = { quiz: 0, open_ended: 0, practice: 0, flashcard: 0, tutor: 0 }
  for (const c of dash) {
    if (!c.streams) continue
    for (const k of Object.keys(streamTotals)) streamTotals[k] += c.streams[k]?.count ?? 0
  }
  const totalEffort = Object.values(streamTotals).reduce((s, v) => s + v, 0)
  const recogCount = (streamTotals.quiz ?? 0) + (streamTotals.practice ?? 0)
  const appliedCount = totalEffort - recogCount
  const gapMismatches = dash.filter((c) => c.mismatch?.mismatch_type === "mcq_high_applied_low").length
  const effortVerdict = totalEffort === 0
    ? "No practice volume yet — effort analysis appears after your first sessions."
    : gapMismatches > 0 && recogCount > appliedCount * 2
      ? `Recognition is saturated (${gapMismatches} concept${gapMismatches === 1 ? "" : "s"} where recall outruns understanding) — switch volume to explain-back and flashcards.`
      : data.avg_applied !== null && data.avg_mcq !== null && data.avg_mcq - data.avg_applied > 20
        ? "Applied mastery trails recognition by 20+ points — add open-ended practice to convert knowledge into skill."
        : "Effort looks balanced across recognition and application — keep the mix."

  // Calibration quadrants: x = confidence, y = correctness.
  const quad = { calibrated: 0, over: 0, under: 0, lost: 0 }
  for (const p of scatter) {
    if (p.confidence >= 50 && p.correctness >= 50) quad.calibrated += 1
    else if (p.confidence >= 50) quad.over += 1
    else if (p.correctness >= 50) quad.under += 1
    else quad.lost += 1
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        title="Analytics"
        subtitle="Evidence-based view of your learning activity and progress"
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Materials" value={data.materials_total} icon={<FileText size={16} />} />
        <StatCard
          label="Concepts"
          value={data.core_concepts_count}
          sub={`of ${data.concepts_count} total`}
          icon={<Brain size={16} />}
        />
        <StatCard
          label="Quiz Attempts"
          value={data.quiz_attempts_completed}
          icon={<HelpCircle size={16} />}
        />
        <StatCard label="Flashcards" value={data.flashcards_total} icon={<CreditCard size={16} />} />
        <StatCard label="Tutor Q&A" value={data.tutor_interactions} icon={<MessageCircle size={16} />} />
        <StatCard
          label="Assessments"
          value={data.assessments_total}
          icon={<ClipboardCheck size={16} />}
        />
      </div>

      {!hasEvidence ? (
        <div className="rounded-xl border border-slate-200 bg-white">
          <EmptyState
            icon={<HelpCircle size={24} />}
            title="No learning evidence yet"
            hint="Answer a quiz, review flashcards, or explain a concept back — your charts will appear here."
          />
        </div>
      ) : (
        <>
          <div className="flex gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1">
            {LAB_TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`shrink-0 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors ${tab === t.id ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {t.label}
              </button>
            ))}
          </div>
          {tab === "overview" && (
          <>
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-800">Mastery Over Time</div>
                <div className="mt-0.5 text-xs text-slate-400">
                  MCQ and Applied mastery trends from your quiz and assessment history
                </div>
              </div>
              <div className="flex gap-1">
                {(["2w", "1m", "all"] as Range[]).map((f) => (
                  <button
                    key={f}
                    type="button"
                    className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                      range === f ? "bg-indigo-600 text-white" : "text-slate-500 hover:bg-slate-100"
                    }`}
                    onClick={() => setRange(f)}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
            {timeline.length < 2 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                Not enough history yet — keep studying to reveal a trend.
              </p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={timeline} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="mcqGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="appliedGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "#94a3b8" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "#94a3b8" }}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                    />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: "#64748b" }} />
                    <Area
                      type="monotone"
                      dataKey="mcq"
                      name="MCQ"
                      stroke="#4f46e5"
                      strokeWidth={2}
                      fill="url(#mcqGrad)"
                      dot={{ r: 3, fill: "#4f46e5" }}
                      connectNulls
                    />
                    <Area
                      type="monotone"
                      dataKey="applied"
                      name="Applied"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#appliedGrad)"
                      dot={{ r: 3, fill: "#10b981" }}
                      connectNulls
                    />
                  </AreaChart>
                </ResponsiveContainer>
                <div className="mt-3 text-center text-xs text-slate-400">
                  {timeline.length} data points — keep studying to reveal a more reliable trend
                </div>
              </>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-1 text-sm font-semibold text-slate-800">
              MCQ vs. Applied Mastery by Topic
            </div>
            <div className="mb-5 text-xs text-slate-400">
              The gap between these bars reveals recognition vs. application ability
            </div>
            {topics.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-500">No topics yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={topics} margin={{ top: 5, right: 10, left: -20, bottom: 0 }} barCategoryGap="30%">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="topic"
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#94a3b8" }}
                    axisLine={false}
                    tickLine={false}
                    domain={[0, 100]}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: "#64748b" }} />
                  <Bar dataKey="mcq" name="MCQ" fill="#4f46e5" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="applied" name="Applied" fill="#10b981" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {dash.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <div className="mb-1 text-sm font-semibold text-slate-800">Mastery distribution</div>
              <div className="mb-4 text-xs text-slate-400">
                Averages hide shape — this shows where your {dash.length} practice concepts actually sit
              </div>
              <div className="space-y-2.5">
                {distBands.map((b) => (
                  <div key={b.label} className="flex items-center gap-3">
                    <span className="w-24 shrink-0 text-xs text-slate-500">{b.label}</span>
                    <div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div className={`h-full rounded-full ${b.color}`} style={{ width: `${(b.count / distMax) * 100}%` }} />
                    </div>
                    <span className="font-mono-data w-8 shrink-0 text-right text-xs font-semibold text-slate-700">{b.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          </>
          )}
          {tab === "calibration" && (
          <>
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-1 text-sm font-semibold text-slate-800">Calibration matrix</div>
            <div className="mb-4 text-xs text-slate-400">
              Each dot is a concept — click one to study it. Top-left (sure but wrong) means slow down and explain back;
              bottom-right (unsure but right) means trust yourself and attempt harder.
            </div>
            {scatter.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-500">
                No confidence data yet — answer graded quiz questions with a confidence rating to
                calibrate this view.
              </p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={260}>
                  <ScatterChart margin={{ top: 10, right: 20, left: -10, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis
                      type="number"
                      dataKey="confidence"
                      name="Confidence"
                      tick={{ fontSize: 11, fill: "#94a3b8" }}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                      label={{
                        value: "Confidence →",
                        position: "insideBottomRight",
                        offset: -5,
                        fontSize: 11,
                        fill: "#94a3b8",
                      }}
                    />
                    <YAxis
                      type="number"
                      dataKey="correctness"
                      name="Correctness"
                      tick={{ fontSize: 11, fill: "#94a3b8" }}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                      label={{
                        value: "Correctness →",
                        angle: -90,
                        position: "insideLeft",
                        offset: 15,
                        fontSize: 11,
                        fill: "#94a3b8",
                      }}
                    />
                    <ReferenceLine x={50} stroke="#e2e8f0" strokeDasharray="4 4" />
                    <ReferenceLine y={50} stroke="#e2e8f0" strokeDasharray="4 4" />
                    <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="#fff7ed" fillOpacity={0.9} />
                    <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="#ecfdf5" fillOpacity={0.9} />
                    <Tooltip content={<ScatterTooltip />} />
                    <Scatter
                      data={scatter}
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      onClick={(p: any) => {
                        const id = p?.payload?.concept_id as string | undefined
                        if (id) practice(id)
                      }}
                      style={{ cursor: "pointer" }}
                    >
                      {scatter.map((d, i) => {
                        const mismatch = d.confidence > 60 && d.correctness < 65
                        const strong = d.confidence > 60 && d.correctness >= 65
                        const under = d.confidence <= 60 && d.correctness >= 65
                        return (
                          <Cell
                            key={i}
                            fill={mismatch ? "#f97316" : strong ? "#4f46e5" : under ? "#10b981" : "#94a3b8"}
                          />
                        )
                      })}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
                <div className="mt-2 flex flex-wrap gap-4 text-xs">
                  {[
                    { label: "Strong understanding", color: "bg-indigo-500" },
                    { label: "Critical mismatch", color: "bg-orange-500" },
                    { label: "Underconfidence", color: "bg-emerald-500" },
                    { label: "Needs practice", color: "bg-slate-400" },
                  ].map((l) => (
                    <div key={l.label} className="flex items-center gap-1.5">
                      <div className={`h-2.5 w-2.5 rounded-full ${l.color}`} />
                      <span className="text-slate-500">{l.label}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-600">
                  {quad.over > 0
                    ? `${quad.over} concept${quad.over === 1 ? " is" : "s are"} overconfident (sure but wrong) — explain-back beats more quizzes there.`
                    : quad.under > 0
                      ? `${quad.under} underconfident — you know more than you trust. Attempt harder questions.`
                      : quad.calibrated > 0
                        ? `${quad.calibrated} calibrated — push difficulty up to keep growing.`
                        : "No calibration signal yet — answer with confidence ratings to fill this in."}
                  {quad.lost > 0 && ` ${quad.lost} still in the foundations corner.`}
                </p>
              </>
            )}
          </div>
          </>
          )}
          {tab === "overview" && (
          <>
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-4 text-sm font-semibold text-slate-800">Before vs. Now</div>
            {data.before_now.length === 0 ? (
              <p className="py-4 text-center text-sm text-slate-500">
                Practice a concept at least twice to see your growth here.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-3">
                {data.before_now.map((item) => (
                  <div key={item.concept_id} className="rounded-xl border border-slate-100 p-4">
                    <div className="mb-3 text-xs font-semibold text-slate-600">{item.concept}</div>
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div>
                        <div className="mb-1 text-xs text-slate-400">Earlier</div>
                        <div className="font-mono-data text-xs text-slate-500">
                          MCQ {fmtPct(item.early_mcq)}
                        </div>
                        <div className="font-mono-data text-xs text-slate-500">
                          Applied {fmtPct(item.early_applied)}
                        </div>
                      </div>
                      <div>
                        <div className="mb-1 text-xs text-slate-400">Current</div>
                        <div className="font-mono-data text-xs font-semibold text-green-600">
                          MCQ {fmtPct(item.current_mcq)}
                        </div>
                        <div className="font-mono-data text-xs font-semibold text-green-600">
                          Applied {fmtPct(item.current_applied)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          </>
          )}
          {tab === "forgetting" && (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <div className="mb-1 text-sm font-semibold text-slate-800">Review before it fades</div>
              <div className="mb-4 text-xs text-slate-400">
                Solid mastery untouched for 14+ days. Proactive review beats re-learning — oldest first.
              </div>
              {fading.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-500">
                  Nothing fading — no strong concept has gone 14 days without practice.
                </p>
              ) : (
                <div className="space-y-2.5">
                  {fading.map((c) => (
                    <div key={c.concept_id} className="flex items-center gap-3 rounded-lg border border-slate-100 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-slate-800">{c.title}</div>
                        <div className="mt-0.5 text-xs text-slate-400">
                          {c.mcq !== null ? `${Math.round(c.mcq)}% MCQ` : "no MCQ yet"} · untouched {c.days} days
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => practice(c.concept_id)}
                        className="shrink-0 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
                      >
                        Review →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {tab === "effort" && (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <div className="mb-1 text-sm font-semibold text-slate-800">Effort vs. outcome</div>
              <div className="mb-4 text-xs text-slate-400">
                Where your evidence volume goes, by stream — against what your mastery says
              </div>
              {totalEffort === 0 ? (
                <p className="py-6 text-center text-sm text-slate-500">
                  No practice volume yet — effort analysis appears after your first sessions.
                </p>
              ) : (
                <>
                  <div className="space-y-2.5">
                    {[
                      { label: "Quiz (exam)", key: "quiz", color: "bg-indigo-500" },
                      { label: "Practice (MCQ)", key: "practice", color: "bg-violet-400" },
                      { label: "Open-ended", key: "open_ended", color: "bg-emerald-500" },
                      { label: "Flashcards", key: "flashcard", color: "bg-amber-400" },
                      { label: "Tutor checks", key: "tutor", color: "bg-sky-400" },
                    ].map((s) => (
                      <div key={s.key} className="flex items-center gap-3">
                        <span className="w-32 shrink-0 text-xs text-slate-500">{s.label}</span>
                        <div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full ${s.color}`}
                            style={{ width: `${(streamTotals[s.key] / Math.max(1, totalEffort)) * 100}%` }}
                          />
                        </div>
                        <span className="font-mono-data w-10 shrink-0 text-right text-xs font-semibold text-slate-700">
                          {streamTotals[s.key]}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-600">
                    {effortVerdict}
                  </p>
                </>
              )}
            </div>
          )}
          {tab === "growth" && (
            <GrowthView projectId={projectId} />
          )}
        </>
      )}
    </div>
  )
}
