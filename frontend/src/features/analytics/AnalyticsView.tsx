import { useCallback, useEffect, useState } from "react"
import { BookOpenText, BrainCircuit, ListTree, MessagesSquare, Target, Trophy } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { ErrorBox, LoadingState } from "@/components/ui"

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
      const { status, message: detail } = apiError(e)
      if (status === 404) setError("Project not found for this view.")
      else setError(detail ?? "Failed to load analytics.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <LoadingState text="Loading analytics…" />
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />
  if (!data) return null

  const cards = [
    { icon: BookOpenText, tint: "bg-rose-100 text-rose-600", label: "Materials", value: `${data.materials_total}` },
    { icon: ListTree, tint: "bg-indigo-100 text-indigo-600", label: "Topics / concepts", value: `${data.topics_count} / ${data.concepts_count}` },
    { icon: Trophy, tint: "bg-amber-100 text-amber-600", label: "Quizzes done", value: `${data.quiz_attempts_completed}/${data.quiz_attempts}` },
    { icon: Target, tint: "bg-violet-100 text-violet-600", label: "Avg recognition", value: fmt(data.avg_mcq) },
    { icon: BrainCircuit, tint: "bg-fuchsia-100 text-fuchsia-600", label: "Avg applied", value: fmt(data.avg_applied) },
    { icon: MessagesSquare, tint: "bg-sky-100 text-sky-600", label: "Tutor chats", value: "soon" },
  ]

  return (
    <div>
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border bg-card p-3.5 shadow-soft">
            <span className={`inline-flex h-8 w-8 items-center justify-center rounded-lg ${c.tint}`}>
              <c.icon className="h-4 w-4" />
            </span>
            <p className="mt-2 text-xl font-extrabold tracking-tight">{c.value}</p>
            <p className="text-xs font-medium text-muted-foreground">{c.label}</p>
          </div>
        ))}
      </div>
      {Object.keys(data.materials_by_status).length > 0 && (
        <p className="mt-3 text-xs text-muted-foreground">
          Materials:{" "}
          {Object.entries(data.materials_by_status)
            .map(([status, count]) => `${status} ${count}`)
            .join(" · ")}
        </p>
      )}
    </div>
  )
}
