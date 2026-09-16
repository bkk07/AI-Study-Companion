import { useCallback, useEffect, useState } from "react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"

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
  if (value === null) return "not enough history"
  const sign = value > 0 ? "+" : ""
  return `${sign}${value.toFixed(1)} points`
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

  if (loading) return <p className="mt-2 text-sm text-muted-foreground">Loading growth…</p>
  if (error)
    return (
      <div className="mt-2">
        <p className="text-sm text-destructive">{error}</p>
        <button onClick={() => void loadOverview()} className="mt-1 text-sm text-primary hover:underline">
          Retry
        </button>
      </div>
    )
  if (!overview) return null

  return (
    <div className="mt-2 space-y-4">
      {overview.total_evidence === 0 ? (
        <p className="text-sm text-muted-foreground">
          No evidence yet — answer quizzes or explain a concept back, then your growth will appear here.
        </p>
      ) : (
        <div className="rounded-md border bg-card px-3 py-2">
          <p className="text-sm font-medium">Overall progress</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Recognition {fmt(overview.avg_mcq)} · Applied {fmt(overview.avg_applied)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {overview.evidenced_concepts} concept(s) with evidence · {overview.total_evidence} evidence total
            {overview.since && overview.until
              ? ` · ${new Date(overview.since).toLocaleDateString()} → ${new Date(overview.until).toLocaleDateString()}`
              : ""}
          </p>
        </div>
      )}

      {overview.concepts.length > 0 && (
        <div>
          <label className="text-sm font-medium" htmlFor="growth-concept">
            Concept history
          </label>
          <select
            id="growth-concept"
            value={selected}
            onChange={(e) => void selectConcept(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-2 py-1.5 text-sm"
          >
            <option value="">Select a concept…</option>
            {overview.concepts.map((c) => (
              <option key={c.concept_id} value={c.concept_id}>
                {c.title} ({c.count} evidence)
              </option>
            ))}
          </select>
          {seriesLoading ? (
            <p className="mt-2 text-sm text-muted-foreground">Loading history…</p>
          ) : series ? (
            <div className="mt-2 rounded-md border bg-card px-3 py-2">
              <p className="text-sm">
                Recognition trend: <span className="font-medium">{fmtSigned(series.mcq_trend)}</span>
                {" · "}Applied trend: <span className="font-medium">{fmtSigned(series.applied_trend)}</span>
              </p>
              {series.points.length === 0 ? (
                <p className="mt-1 text-sm text-muted-foreground">No history for this concept yet.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {series.points.map((p, i) => (
                    <li key={i} className="text-xs text-muted-foreground">
                      {new Date(p.at).toLocaleString()} · {p.evidence_type} {p.raw_score.toFixed(0)} → recognition{" "}
                      {fmt(p.mcq_after)}, applied {fmt(p.applied_after)}
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
