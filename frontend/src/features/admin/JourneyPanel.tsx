import { useCallback, useEffect, useState } from "react"
import { ArrowLeft, Map } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, StatCard } from "@/components/ui"
import type { UserJourney } from "@/features/admin/types"

export function JourneyPanel({ userId, onBack }: { userId: string; onBack: () => void }) {
  const [data, setData] = useState<UserJourney | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<UserJourney>(`/admin/users/${userId}/journey`)
      setData(res.data)
    } catch (e: unknown) {
      const { message } = apiError(e)
      setError(message ?? "Failed to load user journey.")
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <LoadingState text="Loading journey…" />
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />
  if (!data) return <EmptyState icon={<Map size={22} />} title="No data" hint="Journey unavailable." />

  return (
    <div>
      <button
        type="button"
        onClick={onBack}
        className="mb-4 flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:underline"
      >
        <ArrowLeft size={16} /> Back to users
      </button>
      <h2 className="text-lg font-semibold text-slate-900">{data.email}</h2>
      <p className="mb-4 text-xs text-slate-500">
        {data.projects.length} projects · {data.mastery.evidence_rows} evidence rows ·{" "}
        {data.spend.calls} LLM calls
        {data.spend.cost_usd !== null ? ` · $${data.spend.cost_usd.toFixed(4)} spend` : ""}
      </p>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Projects" value={data.projects.length} />
        <StatCard label="Evidence" value={data.mastery.evidence_rows} />
        <StatCard
          label="Avg score"
          value={data.mastery.avg_score === null ? "—" : `${Math.round(data.mastery.avg_score)}%`}
        />
        <StatCard label="LLM calls" value={data.spend.calls} />
      </div>

      <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="text-sm font-semibold text-slate-800">Projects</h3>
        </div>
        {data.projects.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">No projects yet.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {data.projects.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 last:border-0">
                  <td className="px-6 py-3 font-medium text-slate-800">{p.name}</td>
                  <td className="px-6 py-3 text-right text-xs text-slate-500">
                    {new Date(p.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="text-sm font-semibold text-slate-800">Recent quiz attempts</h3>
        </div>
        {data.recent_attempts.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">No attempts yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Score</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Started</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Completed</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_attempts.map((a) => (
                  <tr key={a.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono-data font-bold text-slate-900">
                      {a.score === null ? "—" : `${Math.round(a.score)}%`}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {a.started_at ? new Date(a.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {a.completed_at ? new Date(a.completed_at).toLocaleString() : "open"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="text-sm font-semibold text-slate-800">Event timeline</h3>
        </div>
        {data.recent_events.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">No events yet.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {data.recent_events.map((e) => (
                <tr key={e.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-500">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700">
                      {e.event_type}
                    </span>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-slate-500">
                    {JSON.stringify(e.payload)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
