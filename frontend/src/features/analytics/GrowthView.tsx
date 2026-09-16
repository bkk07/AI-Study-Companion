import { useCallback, useEffect, useState } from "react"
import { TrendingDown, TrendingUp } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Badge, EmptyState, ErrorBox, LoadingState, ProgressBar, Select } from "@/components/ui"

type GrowthPoint = {
  at: string
  evidence_type: string
  raw_score: number
  mcq_after: number | null
  applied_after: number | null
}

type ConceptGrowth = {
  concept_id: string
  points: GrowthPoint[]
  mcq_trend: number | null
  applied_trend: number | null
  count: number
}

type ConceptCurrent = {
  concept_id: string
  title: string
  mcq: number | null
  applied: number | null
  count: number
}

type ProjectGrowth = {
  concepts: ConceptCurrent[]
  avg_mcq: number | null
  avg_applied: number | null
  evidenced_concepts: number
  total_evidence: number
  since: string | null
  until: string | null
}

function fmt(value: number | null): string {
  return value === null ? "—" : value.toFixed(1)
}

function fmtSigned(value: number | null): string {
  if (value === null) return "—"
  const sign = value > 0 ? "+" : ""
  return `${sign}${value.toFixed(1)} points`
}

function TrendBadge({ value }: { value: number | null }) {
  if (value === null) return <Badge tint="muted">—</Badge>
  const up = value > 0
  const flat = value === 0
  return (
    <Badge tint={up ? "emerald" : flat ? "muted" : "rose"}>
      {up ? <TrendingUp className="h-3 w-3" /> : flat ? null : <TrendingDown className="h-3 w-3" />}
      {fmtSigned(value)}
    </Badge>
  )
}

function Sparkline({ points }: { points: GrowthPoint[] }) {
  const mcq = points.map((p) => p.mcq_after).filter((v): v is number => v !== null)
  const applied = points.map((p) => p.applied_after).filter((v): v is number => v !== null)
  if (mcq.length < 2 && applied.length < 2) return null

  const line = (values: number[], n: number) => {
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = max - min || 1
    return values
      .map((v, i) => `${((i / (n - 1)) * 100).toFixed(1)},${(30 - ((v - min) / span) * 26).toFixed(1)}`)
      .join(" ")
  }

  return (
    <svg viewBox="0 0 100 32" className="mt-3 h-16 w-full" role="img" aria-label="Mastery trend">
      <defs>
        <linearGradient id="spark-mcq" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#8b5cf6" />
          <stop offset="1" stopColor="#d946ef" />
        </linearGradient>
      </defs>
      {[8, 16, 24].map((y) => (
        <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="hsl(250 25% 90%)" strokeWidth="0.5" />
      ))}
      {applied.length >= 2 && (
        <polyline points={line(applied, points.length)} fill="none" stroke="#10b981" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      )}
      {mcq.length >= 2 && (
        <polyline points={line(mcq, points.length)} fill="none" stroke="url(#spark-mcq)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  )
}

export function GrowthView({ projectId }: { projectId: string }) {
  const [overview, setOverview] = useState<ProjectGrowth | null>(null)
  const [selected, setSelected] = useState<string>("")
  const [series, setSeries] = useState<ConceptGrowth | null>(null)
  const [loading, setLoading] = useState(true)
  const [seriesLoading, setSeriesLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<ProjectGrowth>(`/projects/${projectId}/growth`)
      setOverview(res.data)
      setSeries(null)
      setSelected("")
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 404) setError("Project not found for this view.")
      else setError(detail ?? "Failed to load growth.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void loadOverview()
  }, [loadOverview])

  async function selectConcept(conceptId: string) {
    setSelected(conceptId)
    if (!conceptId) {
      setSeries(null)
      return
    }
    setSeriesLoading(true)
    try {
      const res = await apiClient.get<ConceptGrowth>(`/projects/${projectId}/growth`, {
        params: { concept_id: conceptId },
      })
      setSeries(res.data)
    } catch (e: unknown) {
      const { message: detail } = apiError(e)
      setError(detail ?? "Failed to load concept history.")
    } finally {
      setSeriesLoading(false)
    }
  }

  if (loading) return <LoadingState text="Loading growth…" />
  if (error) return <ErrorBox message={error} onRetry={() => void loadOverview()} />
  if (!overview) return null

  return (
    <div className="space-y-4">
      {overview.total_evidence === 0 ? (
        <EmptyState
          icon={<TrendingUp className="h-6 w-6" />}
          title="Your curve starts here"
          hint="Answer quizzes or explain a concept back, then watch your mastery climb."
        />
      ) : (
        <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 p-5 text-white shadow-soft">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-white/70">Overall progress</p>
          <div className="mt-3 space-y-2.5">
            <div>
              <div className="flex justify-between text-xs font-semibold">
                <span>Recognition</span>
                <span>{fmt(overview.avg_mcq)}</span>
              </div>
              <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-white/20">
                <div
                  className="h-full rounded-full bg-white transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, overview.avg_mcq ?? 0))}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs font-semibold">
                <span>Applied</span>
                <span>{fmt(overview.avg_applied)}</span>
              </div>
              <ProgressBar value={overview.avg_applied} className="mt-1 bg-white/20" barClass="from-amber-300 to-orange-400" />
            </div>
          </div>
          <p className="mt-3 text-xs text-white/75">
            {overview.evidenced_concepts} concept(s) with evidence · {overview.total_evidence} evidence total
            {overview.since && overview.until
              ? ` · ${new Date(overview.since).toLocaleDateString()} → ${new Date(overview.until).toLocaleDateString()}`
              : ""}
          </p>
        </div>
      )}

      {overview.concepts.length > 0 && (
        <div>
          <label className="text-sm font-bold" htmlFor="growth-concept">
            Concept history
          </label>
          <Select
            id="growth-concept"
            value={selected}
            onChange={(e) => void selectConcept(e.target.value)}
            className="mt-1.5"
          >
            <option value="">Select a concept…</option>
            {overview.concepts.map((c) => (
              <option key={c.concept_id} value={c.concept_id}>
                {c.title} ({c.count} evidence)
              </option>
            ))}
          </Select>
          {seriesLoading ? (
            <LoadingState text="Loading history…" />
          ) : series ? (
            <div className="animate-fade-up mt-2.5 rounded-2xl border bg-card p-4 shadow-soft">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-semibold">Recognition</span>
                <TrendBadge value={series.mcq_trend} />
                <span className="font-semibold">Applied</span>
                <TrendBadge value={series.applied_trend} />
              </div>
              <div className="mt-1 flex items-center gap-4 text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <span className="h-0.5 w-4 rounded bg-gradient-to-r from-violet-500 to-fuchsia-500" /> recognition
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-0.5 w-4 rounded bg-emerald-500" /> applied
                </span>
              </div>
              <Sparkline points={series.points} />
              {series.points.length === 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">No history for this concept yet.</p>
              ) : (
                <ul className="mt-3 space-y-1.5 border-t border-dashed pt-3">
                  {series.points.map((p, i) => (
                    <li key={i} className="text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">{new Date(p.at).toLocaleDateString()}</span>
                      {" · "}{p.evidence_type} {p.raw_score.toFixed(0)} → recognition {fmt(p.mcq_after)}, applied{" "}
                      {fmt(p.applied_after)}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
