import { useCallback, useEffect, useMemo, useState } from "react"
import { FlaskConical } from "lucide-react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, StatCard } from "@/components/ui"
import type { AIEvaluation } from "@/features/admin/types"

type RangePreset = "7d" | "30d" | "all"

const PRESETS: { id: RangePreset; label: string }[] = [
  { id: "7d", label: "7d" },
  { id: "30d", label: "30d" },
  { id: "all", label: "All" },
]

function fmtPct(v: number | null | undefined, digits = 1): string {
  return v === null || v === undefined ? "—" : `${(v * 100).toFixed(digits)}%`
}

function fmtNum(v: number | null | undefined, digits = 2): string {
  return v === null || v === undefined ? "—" : v.toFixed(digits)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function TrendTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-medium text-slate-700">{label}</div>
      {payload.map((p: { name: string; value: number | null; color?: string }) => (
        <div key={p.name} className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-slate-500">{p.name}:</span>
          <span className="font-semibold text-slate-800">
            {p.value === null || p.value === undefined ? "—" : `${p.value}%`}
          </span>
        </div>
      ))}
    </div>
  )
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{children}</h3>
}

export function EvaluationPanel() {
  const [data, setData] = useState<AIEvaluation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [preset, setPreset] = useState<RangePreset>("30d")

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (preset !== "all") {
        const days = preset === "7d" ? 7 : 30
        params.since = new Date(Date.now() - days * 86400_000).toISOString()
      }
      const res = await apiClient.get<AIEvaluation>("/admin/ai-evaluation", { params })
      setData(res.data)
    } catch (e: unknown) {
      const { message } = apiError(e)
      setError(message ?? "Failed to load AI evaluation.")
    } finally {
      setLoading(false)
    }
  }, [preset])

  useEffect(() => {
    void load()
  }, [load])

  const trendData = useMemo(
    () =>
      (data?.trends ?? []).map((t) => ({
        week: t.week.slice(5),
        supported_rate: t.supported_rate == null ? null : Math.round(t.supported_rate * 1000) / 10,
      })),
    [data],
  )

  const isEmpty =
    data !== null &&
    (data.tutor.answers ?? 0) === 0 &&
    (data.retrieval.calls ?? 0) === 0 &&
    (data.assessment.mcq_attempts ?? 0) === 0 &&
    (data.assessment.open_ended_grades ?? 0) === 0 &&
    (data.recommendations.total ?? 0) === 0

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPreset(p.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              preset === p.id
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {p.label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <LoadingState text="Loading AI evaluation…" />
      ) : error ? (
        <ErrorBox message={error} onRetry={() => void load()} />
      ) : !data || isEmpty ? (
        <EmptyState
          icon={<FlaskConical size={22} />}
          title="No evaluation data"
          hint="No tutor, assessment, or recommendation activity in this range yet."
        />
      ) : (
        <>
          <SectionTitle>Tutor quality</SectionTitle>
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Answers" value={(data.tutor.answers ?? 0).toLocaleString()} />
            <StatCard label="Supported" value={(data.tutor.supported ?? 0).toLocaleString()} accent="green" />
            <StatCard label="Unsupported" value={(data.tutor.unsupported ?? 0).toLocaleString()} accent="red" />
            <StatCard label="Supported rate" value={fmtPct(data.tutor.supported_rate)} accent="indigo" />
            <StatCard label="Citation coverage" value={fmtPct(data.tutor.citation_coverage)} />
            <StatCard label="Avg citations" value={fmtNum(data.tutor.avg_citations)} />
          </div>

          {trendData.length > 1 && (
            <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">Supported rate by week (%)</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="week" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" domain={[0, 100]} />
                    <Tooltip content={<TrendTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="supported_rate"
                      name="Supported"
                      stroke="#4f46e5"
                      fill="#c7d2fe"
                      strokeWidth={2}
                      connectNulls={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <SectionTitle>Retrieval grounding</SectionTitle>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Tutor calls" value={(data.retrieval.calls ?? 0).toLocaleString()} />
            <StatCard label="Avg chunks" value={fmtNum(data.retrieval.avg_chunks)} />
            <StatCard label="Avg top distance" value={fmtNum(data.retrieval.avg_top_distance, 3)} />
            <StatCard label="Zero-context rate" value={fmtPct(data.retrieval.zero_context_rate)} accent="amber" />
          </div>

          {data.retrieval.by_model.length > 0 && (
            <div className="mb-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-6 py-4">
                <h3 className="text-sm font-semibold text-slate-800">Retrieval by model</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Model</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Calls</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Avg chunks</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Avg top distance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.retrieval.by_model.map((r) => (
                      <tr key={r.model} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                        <td className="max-w-48 truncate px-4 py-3 font-mono text-xs text-slate-700">{r.model}</td>
                        <td className="px-4 py-3 text-right font-mono-data text-slate-900">{(r.calls ?? 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-mono-data text-slate-900">{fmtNum(r.avg_chunks)}</td>
                        <td className="px-4 py-3 text-right font-mono-data text-slate-900">{fmtNum(r.avg_top_distance, 3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <SectionTitle>Assessment quality</SectionTitle>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="MCQ attempts" value={(data.assessment.mcq_attempts ?? 0).toLocaleString()} />
            <StatCard label="MCQ avg score" value={fmtNum(data.assessment.mcq_avg_score)} accent="indigo" />
            <StatCard label="Open-ended grades" value={(data.assessment.open_ended_grades ?? 0).toLocaleString()} />
            <StatCard label="Open-ended avg" value={fmtNum(data.assessment.open_ended_avg_score)} />
            <StatCard
              label="Verdict pass"
              value={(data.assessment.verdict_bands?.pass ?? 0).toLocaleString()}
              accent="green"
            />
            <StatCard
              label="Verdict fail"
              value={(data.assessment.verdict_bands?.fail ?? 0).toLocaleString()}
              accent="red"
              sub={`Partial: ${(data.assessment.verdict_bands?.partial ?? 0).toLocaleString()}`}
            />
          </div>

          {data.assessment.accuracy_by_difficulty.length > 0 && (
            <div className="mb-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-6 py-4">
                <h3 className="text-sm font-semibold text-slate-800">Accuracy by difficulty</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Difficulty</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Answered</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Correct</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Accuracy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.assessment.accuracy_by_difficulty.map((d) => (
                      <tr key={d.difficulty} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                        <td className="px-4 py-3 font-mono text-xs text-slate-700">{d.difficulty}</td>
                        <td className="px-4 py-3 text-right font-mono-data text-slate-900">{(d.answered ?? 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-mono-data text-slate-900">{(d.correct ?? 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-mono-data text-slate-900">{fmtPct(d.accuracy)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <SectionTitle>Recommendations</SectionTitle>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Total" value={(data.recommendations.total ?? 0).toLocaleString()} />
            <StatCard label="Active" value={(data.recommendations.active ?? 0).toLocaleString()} />
            <StatCard label="Accepted" value={(data.recommendations.accepted ?? 0).toLocaleString()} accent="green" />
            <StatCard label="Dismissed" value={(data.recommendations.dismissed ?? 0).toLocaleString()} accent="amber" />
            <StatCard label="Accept rate" value={fmtPct(data.recommendations.accept_rate)} accent="indigo" />
            <StatCard label="Dismiss rate" value={fmtPct(data.recommendations.dismiss_rate)} />
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-6 py-4">
              <h3 className="text-sm font-semibold text-slate-800">Status breakdown</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <tbody>
                  {(
                    [
                      ["Active", data.recommendations.active],
                      ["Accepted", data.recommendations.accepted],
                      ["Dismissed", data.recommendations.dismissed],
                      ["Expired", data.recommendations.expired],
                    ] as const
                  ).map(([label, count]) => (
                    <tr key={label} className="border-b border-slate-50 last:border-0">
                      <td className="px-6 py-3 font-mono text-xs text-slate-700">{label}</td>
                      <td className="px-6 py-3 text-right font-mono-data font-bold text-slate-900">
                        {(count ?? 0).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
