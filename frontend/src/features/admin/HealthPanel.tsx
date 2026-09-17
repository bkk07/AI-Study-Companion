import { useCallback, useEffect, useState } from "react"
import { HeartPulse } from "lucide-react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, StatCard } from "@/components/ui"
import type { Health } from "@/features/admin/types"

const STATUS_COLORS: Record<string, string> = {
  completed: "#10b981",
  failed: "#f43f5e",
  running: "#f59e0b",
  pending: "#94a3b8",
}

export function HealthPanel() {
  const [data, setData] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<Health>("/admin/health")
      setData(res.data)
    } catch (e: unknown) {
      const { message } = apiError(e)
      setError(message ?? "Failed to load system health.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <LoadingState text="Loading health…" />
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />
  if (!data) return <EmptyState icon={<HeartPulse size={22} />} title="No data" hint="Health data unavailable." />

  return (
    <div>
      <div className="mb-4 grid grid-cols-2 gap-3">
        <StatCard label="Failed jobs (24h)" value={data.failed_job_count_24h} accent="red" />
        <StatCard label="Failed LLM calls (24h)" value={data.failed_llm_count_24h} accent="amber" />
      </div>

      {data.jobs_by_status.length > 0 && (
        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Jobs by status (all time)</h3>
          <div className="flex items-center gap-6">
            <div className="h-40 w-40 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.jobs_by_status}
                    dataKey="count"
                    nameKey="status"
                    innerRadius={45}
                    outerRadius={65}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {data.jobs_by_status.map((s) => (
                      <Cell key={s.status} fill={STATUS_COLORS[s.status] ?? "#cbd5e1"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="space-y-2 text-sm">
              {data.jobs_by_status.map((s) => (
                <li key={s.status} className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: STATUS_COLORS[s.status] ?? "#cbd5e1" }}
                  />
                  <span className="font-mono text-xs text-slate-600">{s.status}</span>
                  <span className="font-mono-data font-bold text-slate-900">{s.count.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="text-sm font-semibold text-slate-800">Recent job failures</h3>
        </div>
        {data.failed_jobs.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">No failed jobs — all workflows healthy.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Time</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Job type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Error</th>
                </tr>
              </thead>
              <tbody>
                {data.failed_jobs.map((j) => (
                  <tr key={j.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                      {new Date(j.created_at).toLocaleString()}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">{j.job_type}</td>
                    <td className="max-w-md truncate px-4 py-3 text-xs text-red-600">{j.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="text-sm font-semibold text-slate-800">Recent LLM failures</h3>
        </div>
        {data.failed_llm_calls.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">No failed LLM calls.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Time</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Feature</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Model</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Error</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">ms</th>
                </tr>
              </thead>
              <tbody>
                {data.failed_llm_calls.map((c) => (
                  <tr key={c.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                      {new Date(c.created_at).toLocaleString()}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">{c.feature}</td>
                    <td className="max-w-44 truncate px-4 py-3 font-mono text-xs text-slate-500">{c.model}</td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-red-600">
                      {c.error_type ?? "—"}{c.http_status ? ` · ${c.http_status}` : ""}
                    </td>
                    <td className="px-4 py-3 text-right font-mono-data text-slate-900">{c.latency_ms ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
