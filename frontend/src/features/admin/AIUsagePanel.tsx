import { useCallback, useEffect, useMemo, useState } from "react"
import { Cpu } from "lucide-react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, StatCard } from "@/components/ui"
import type { AIUsageSummary } from "@/features/admin/types"
import { fmtCost, fmtMs, fmtTokens } from "@/features/admin/format"

const ROWS_LIMIT = 25

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CostTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-medium text-slate-700">{label}</div>
      {payload.map((p: { name: string; value: number | null; color?: string }) => (
        <div key={p.name} className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-slate-500">{p.name}:</span>
          <span className="font-semibold text-slate-800">{p.value ?? "—"}</span>
        </div>
      ))}
    </div>
  )
}

export function AIUsagePanel() {
  const [data, setData] = useState<AIUsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [feature, setFeature] = useState("")
  const [provider, setProvider] = useState("")
  const [rowsOffset, setRowsOffset] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (feature.trim()) params.feature = feature.trim()
      if (provider) params.provider = provider
      const res = await apiClient.get<AIUsageSummary>("/admin/ai-usage", { params })
      setData(res.data)
    } catch (e: unknown) {
      const { message } = apiError(e)
      setError(message ?? "Failed to load AI usage.")
    } finally {
      setLoading(false)
    }
  }, [feature, provider])

  useEffect(() => {
    void load()
  }, [load])

  const dailyCost = useMemo(() => {
    const byDay = new Map<string, number>()
    for (const r of data?.rows ?? []) {
      byDay.set(r.day, (byDay.get(r.day) ?? 0) + (r.cost_usd ?? 0))
    }
    return [...byDay.entries()]
      .sort(([a], [b]) => (a < b ? -1 : 1))
      .map(([day, cost]) => ({ day: day.slice(5), cost: Math.round(cost * 1e6) / 1e6 }))
  }, [data])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-xs font-medium text-slate-500">
          Feature
          <input
            value={feature}
            onChange={(e) => {
              setFeature(e.target.value)
              setRowsOffset(0)
            }}
            placeholder="e.g. quiz_generation"
            className="ml-2 w-52 rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono text-xs text-slate-800"
          />
        </label>
        <label className="text-xs font-medium text-slate-500">
          Provider
          <select
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value)
              setRowsOffset(0)
            }}
            className="ml-2 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-800"
          >
            <option value="">All</option>
            <option value="groq">groq</option>
            <option value="inception">inception</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <LoadingState text="Loading AI usage…" />
      ) : error ? (
        <ErrorBox message={error} onRetry={() => void load()} />
      ) : !data || data.calls === 0 ? (
        <EmptyState icon={<Cpu size={22} />} title="No usage" hint="No LLM calls match these filters yet." />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Calls" value={data.calls.toLocaleString()} />
            <StatCard
              label="Tokens"
              value={fmtTokens(data.prompt_tokens + data.completion_tokens)}
            />
            <StatCard label="Cost" value={fmtCost(data.cost_usd)} />
            <StatCard label="Error rate" value={`${(data.error_rate * 100).toFixed(1)}%`} />
            <StatCard label="Latency p50" value={fmtMs(data.latency_p50_ms)} />
            <StatCard label="Latency p95" value={fmtMs(data.latency_p95_ms)} />
          </div>

          {dailyCost.length > 1 && (
            <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">Cost per day (USD)</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dailyCost} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
                    <Tooltip content={<CostTooltip />} />
                    <Area type="monotone" dataKey="cost" name="Cost" stroke="#4f46e5" fill="#c7d2fe" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {data.top_errors.length > 0 && (
            <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-6 py-4">
                <h3 className="text-sm font-semibold text-slate-800">Top errors</h3>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {data.top_errors.map((e) => (
                    <tr key={e.error_type} className="border-b border-slate-50 last:border-0">
                      <td className="px-6 py-3 font-mono text-xs text-slate-700">{e.error_type}</td>
                      <td className="px-6 py-3 text-right font-mono-data font-bold text-slate-900">{e.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-6 py-4">
              <h3 className="text-sm font-semibold text-slate-800">Feature × provider × model × day</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Day</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Feature</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Provider</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Model</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Calls</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Tokens</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Cost</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Avg ms</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.slice(rowsOffset, rowsOffset + ROWS_LIMIT).map((r, i) => (
                    <tr key={`${r.day}-${r.feature}-${r.provider}-${r.model}-${rowsOffset + i}`} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">{r.day}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-700">{r.feature}</td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-500">{r.provider}</td>
                      <td className="max-w-48 truncate px-4 py-3 font-mono text-xs text-slate-500">{r.model}</td>
                      <td className="px-4 py-3 text-right font-mono-data text-slate-900">{r.calls}</td>
                      <td className="px-4 py-3 text-right font-mono-data text-slate-900">
                        {fmtTokens(r.prompt_tokens + r.completion_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono-data text-slate-900">{fmtCost(r.cost_usd)}</td>
                      <td className="px-4 py-3 text-right font-mono-data text-slate-900">{fmtMs(r.avg_latency_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.rows.length > ROWS_LIMIT && (
              <div className="flex items-center gap-3 border-t border-slate-100 px-6 py-3 text-sm text-slate-500">
                <span>
                  {rowsOffset + 1}–{Math.min(rowsOffset + ROWS_LIMIT, data.rows.length)} of {data.rows.length}
                </span>
                <button
                  type="button"
                  disabled={rowsOffset === 0}
                  onClick={() => setRowsOffset(Math.max(0, rowsOffset - ROWS_LIMIT))}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-slate-700 disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  type="button"
                  disabled={rowsOffset + ROWS_LIMIT >= data.rows.length}
                  onClick={() => setRowsOffset(rowsOffset + ROWS_LIMIT)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-slate-700 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
