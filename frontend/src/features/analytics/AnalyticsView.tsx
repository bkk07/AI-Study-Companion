import { useCallback, useEffect, useState } from "react"
import { BookOpenText, BrainCircuit, CreditCard, HelpCircle, Layers, MessageCircle } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { ErrorBox, LoadingState, SectionHeader, StatCard } from "@/components/ui"

type Analytics = {
  materials_total: number
  materials_by_status: Record<string, number>
  topics_count: number
  concepts_count: number
  core_concepts_count: number
  quiz_attempts: number
  quiz_attempts_completed: number
  avg_mcq: number | null
  avg_applied: number | null
  avg_final: number | null
  evidenced_concepts: number
  tutor_interactions: number
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

  return (
    <div>
      <SectionHeader title="Analytics" subtitle="MCQ vs. applied by topic and activity" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Documents" value={data.materials_total} icon={<BookOpenText size={18} />} accent="slate" />
        <StatCard label="Topics" value={data.topics_count} icon={<Layers size={18} />} accent="slate" />
        <StatCard
          label="Concepts"
          value={data.core_concepts_count}
          sub={`of ${data.concepts_count} total`}
          icon={<BrainCircuit size={18} />}
          accent="indigo"
        />
        <StatCard label="Quiz Attempts" value={data.quiz_attempts_completed} sub={`of ${data.quiz_attempts}`} icon={<HelpCircle size={18} />} accent="slate" />
        <StatCard label="Avg MCQ" value={fmt(data.avg_mcq)} icon={<BrainCircuit size={18} />} accent="green" />
        <StatCard label="Avg Applied" value={fmt(data.avg_applied)} icon={<CreditCard size={18} />} accent="amber" />
      </div>
      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <MessageCircle size={15} className="text-slate-400" /> Activity
        </div>
        <p className="mt-1 text-sm text-slate-500">
          {data.evidenced_concepts} evidenced concepts · {data.tutor_interactions} tutor questions
        </p>
        {Object.entries(data.materials_by_status).filter(([, count]) => count > 0).length > 0 && (
          <p className="mt-2 text-xs text-slate-400">
            Materials:{" "}
            {Object.entries(data.materials_by_status)
              .filter(([, count]) => count > 0)
              .map(([status, count]) => `${status} ${count}`)
              .join(" · ")}
          </p>
        )}
      </div>
    </div>
  )
}
