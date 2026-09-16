import { useCallback, useEffect, useState } from "react"
import apiClient from "@/lib/axios"

type Analytics = {
  materials_total: number
  materials_by_status: Record<string, number>
  topics_count: number
  concepts_count: number
  quiz_attempts: number
  quiz_attempts_completed: number
  avg_mcq: number | null
  avg_applied: number | null
  evidenced_concepts: number
  tutor_interactions: null
}

function fmt(value: number | null): string {
  return value === null ? "—" : value.toFixed(1)
}

function extractError(e: unknown): { status?: number; detail?: string } {
  return {
    status: (e as { response?: { status?: number } }).response?.status,
    detail: (e as { response?: { data?: { detail?: string } } }).response?.data?.detail,
  }
}

export function AnalyticsView({ projectId }: { projectId: string }) {
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<Analytics>(`/projects/${projectId}/analytics`)
      setData(res.data)
    } catch (e: unknown) {
      const { status, detail } = extractError(e)
      if (status === 404) setError("Project not found for this view.")
      else setError(detail ?? "Failed to load analytics.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <p className="mt-2 text-sm text-muted-foreground">Loading analytics…</p>
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

  const cards: Array<[string, string]> = [
    ["Materials", `${data.materials_total}`],
    ["Topics / concepts", `${data.topics_count} / ${data.concepts_count}`],
    ["Quiz attempts", `${data.quiz_attempts_completed}/${data.quiz_attempts} completed`],
    ["Avg recognition", fmt(data.avg_mcq)],
    ["Avg applied", fmt(data.avg_applied)],
    ["Tutor chats", "not tracked yet"],
  ]

  return (
    <div className="mt-2">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-md border bg-card px-3 py-2">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-lg font-semibold">{value}</p>
          </div>
        ))}
      </div>
      {Object.keys(data.materials_by_status).length > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          Materials:{" "}
          {Object.entries(data.materials_by_status)
            .map(([status, count]) => `${status} ${count}`)
            .join(" · ")}
        </p>
      )}
    </div>
  )
}
