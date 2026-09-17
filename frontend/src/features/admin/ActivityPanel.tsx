import { useCallback, useEffect, useState } from "react"
import { Activity } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState } from "@/components/ui"
import { EVENT_TYPES, type ActivityPage } from "@/features/admin/types"
import { timeAgo } from "@/features/admin/format"

const TYPE_STYLES: { prefix: string; classes: string }[] = [
  { prefix: "project.", classes: "bg-sky-100 text-sky-700" },
  { prefix: "material.", classes: "bg-amber-100 text-amber-700" },
  { prefix: "tutor.", classes: "bg-violet-100 text-violet-700" },
  { prefix: "quiz.", classes: "bg-emerald-100 text-emerald-700" },
  { prefix: "question.", classes: "bg-teal-100 text-teal-700" },
  { prefix: "assessment.", classes: "bg-indigo-100 text-indigo-700" },
  { prefix: "mastery.", classes: "bg-rose-100 text-rose-700" },
  { prefix: "recommendation.", classes: "bg-orange-100 text-orange-700" },
]

function typeClasses(t: string): string {
  return TYPE_STYLES.find((s) => t.startsWith(s.prefix))?.classes ?? "bg-slate-100 text-slate-600"
}

export function ActivityPanel() {
  const [page, setPage] = useState<ActivityPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [type, setType] = useState("")
  const [userId, setUserId] = useState("")
  const [projectId, setProjectId] = useState("")
  const [offset, setOffset] = useState(0)
  const limit = 25

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { limit, offset }
      if (type) params.type = type
      if (userId.trim()) params.user_id = userId.trim()
      if (projectId.trim()) params.project_id = projectId.trim()
      const res = await apiClient.get<ActivityPage>("/admin/activity", { params })
      setPage(res.data)
    } catch (e: unknown) {
      const { message } = apiError(e)
      setError(message ?? "Failed to load activity.")
    } finally {
      setLoading(false)
    }
  }, [type, userId, projectId, offset])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-xs font-medium text-slate-500">
          Event type
          <select
            value={type}
            onChange={(e) => {
              setType(e.target.value)
              setOffset(0)
            }}
            className="ml-2 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-800"
          >
            <option value="">All</option>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-medium text-slate-500">
          User ID
          <input
            value={userId}
            onChange={(e) => {
              setUserId(e.target.value)
              setOffset(0)
            }}
            placeholder="uuid"
            className="ml-2 w-44 rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono text-xs text-slate-800"
          />
        </label>
        <label className="text-xs font-medium text-slate-500">
          Project ID
          <input
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value)
              setOffset(0)
            }}
            placeholder="uuid"
            className="ml-2 w-44 rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono text-xs text-slate-800"
          />
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
        <LoadingState text="Loading activity…" />
      ) : error ? (
        <ErrorBox message={error} onRetry={() => void load()} />
      ) : !page || page.items.length === 0 ? (
        <EmptyState icon={<Activity size={22} />} title="No events" hint="No learning events match these filters yet." />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Entity</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Payload</th>
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((e) => (
                    <tr key={e.id} className="border-b border-slate-50 transition-colors last:border-0 hover:bg-slate-50">
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500" title={new Date(e.created_at).toLocaleString()}>
                        {timeAgo(e.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 font-mono text-xs font-medium ${typeClasses(e.event_type)}`}>
                          {e.event_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        {e.entity_type ?? "—"} {e.entity_id ? `· ${e.entity_id.slice(0, 8)}` : ""}
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-slate-500">
                        {JSON.stringify(e.payload)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-3 text-sm text-slate-500">
            <span>
              {page.offset + 1}–{page.offset + page.items.length} of {page.total}
            </span>
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-slate-700 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              type="button"
              disabled={offset + limit >= page.total}
              onClick={() => setOffset(offset + limit)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-slate-700 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}
