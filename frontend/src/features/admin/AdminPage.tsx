import { useCallback, useEffect, useRef, useState } from "react"
import {
  Activity,
  BookOpenText,
  BrainCircuit,
  Cpu,
  CreditCard,
  FileUp,
  FolderOpen,
  HeartPulse,
  HelpCircle,
  MessageCircle,
  Search,
  ShieldAlert,
  ShieldCheck,
  Users,
  X,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { useAuth } from "@/context/AuthContext"
import { AppShell } from "@/components/AppShell"
import { Avatar, ErrorBox, LoadingState } from "@/components/ui"
import { Eye } from "lucide-react"
import { ActivityPanel } from "@/features/admin/ActivityPanel"
import { AIUsagePanel } from "@/features/admin/AIUsagePanel"
import { HealthPanel } from "@/features/admin/HealthPanel"
import { JourneyPanel } from "@/features/admin/JourneyPanel"
import { timeAgo } from "@/features/admin/format"
import type { AdminUser, Health, Overview } from "@/features/admin/types"

type Tab = "overview" | "activity" | "ai-usage" | "health"

type UsersPage = {
  items: AdminUser[]
  total: number
  limit: number
  offset: number
}

const USERS_LIMIT = 25

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <Users size={15} /> },
  { id: "activity", label: "Activity", icon: <Activity size={15} /> },
  { id: "ai-usage", label: "AI Usage", icon: <Cpu size={15} /> },
  { id: "health", label: "Health", icon: <HeartPulse size={15} /> },
]

function HeroStat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="font-mono-data text-2xl font-bold text-white sm:text-3xl">{value}</div>
      <div className="mt-0.5 text-xs font-medium uppercase tracking-wider text-indigo-300">{label}</div>
      {sub && <div className="mt-0.5 text-xs text-indigo-300/70">{sub}</div>}
    </div>
  )
}

function StatTile({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-4 transition-shadow hover:shadow-sm">
      <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-600">
        {icon}
      </div>
      <div className="font-mono-data text-2xl font-bold text-slate-900">
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div className="mt-0.5 text-xs text-slate-500">{label}</div>
    </div>
  )
}

export function AdminPage() {
  const { user } = useAuth()
  const [usersPage, setUsersPage] = useState<UsersPage | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("overview")
  const [journeyUserId, setJourneyUserId] = useState<string | null>(null)
  const [userSearch, setUserSearch] = useState("")
  const [userOffset, setUserOffset] = useState(0)

  const loadMeta = useCallback(async () => {
    const [o, h] = await Promise.all([
      apiClient.get<Overview>("/admin/overview"),
      apiClient.get<Health>("/admin/health", { params: { limit: 1 } }),
    ])
    setOverview(o.data)
    setHealth(h.data)
  }, [])

  const loadUsers = useCallback(async () => {
    const params: Record<string, string | number> = { limit: USERS_LIMIT, offset: userOffset }
    if (userSearch.trim()) params.q = userSearch.trim()
    const u = await apiClient.get<UsersPage | AdminUser[]>("/admin/users", { params })
    // Tolerate a stale backend that still returns a bare list: adapt it locally.
    const raw = u.data
    setUsersPage(
      Array.isArray(raw)
        ? {
            items: raw.slice(userOffset, userOffset + USERS_LIMIT).map((r) => ({
              ...r,
              project_count: 0,
              last_active: null,
            })),
            total: raw.length,
            limit: USERS_LIMIT,
            offset: userOffset,
          }
        : raw,
    )
  }, [userSearch, userOffset])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await Promise.all([loadMeta(), loadUsers()])
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 403) setError("Forbidden — admins only.")
      else setError(detail ?? "Failed to load admin data.")
    } finally {
      setLoading(false)
    }
  }, [loadMeta, loadUsers])

  const firstLoad = useRef(true)

  useEffect(() => {
    if (user && !user.is_admin) {
      setLoading(false)
      setError("Forbidden — admins only.")
      return
    }
    if (user && firstLoad.current) {
      firstLoad.current = false
      void load()
    }
  }, [user, load])

  // Paged user browsing must not wipe the hero: refresh the table quietly.
  useEffect(() => {
    if (!user?.is_admin || firstLoad.current) return
    loadUsers().catch(() => undefined)
  }, [user, loadUsers])

  const failures24h = (health?.failed_job_count_24h ?? 0) + (health?.failed_llm_count_24h ?? 0)
  const operational = failures24h === 0

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-8 py-10">
        {/* Command-center hero */}
        <div className="relative mb-6 overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-6 py-6 sm:px-8">
          <div
            className="pointer-events-none absolute inset-0 opacity-40"
            style={{
              backgroundImage: "radial-gradient(circle at 85% 15%, rgba(129,140,248,0.35), transparent 45%)",
            }}
          />
          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
                <ShieldCheck size={20} className="text-white" />
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-widest text-indigo-300">Admin · Mission Control</div>
                <h1 className="text-xl font-semibold text-white">System Overview</h1>
              </div>
            </div>
            {health && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
                  operational
                    ? "bg-emerald-400/10 text-emerald-300 ring-emerald-400/30"
                    : "bg-amber-400/10 text-amber-300 ring-amber-400/30"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${operational ? "bg-emerald-400" : "bg-amber-400"}`} />
                {operational ? "Operational" : `${failures24h} failures · 24h`}
              </span>
            )}
          </div>
          <div className="relative mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
            <HeroStat label="Users" value={(overview?.users ?? 0).toLocaleString()} />
            <HeroStat label="Projects" value={(overview?.projects ?? 0).toLocaleString()} />
            <HeroStat
              label="Quiz attempts · 7d"
              value={(overview?.quiz_attempts_week ?? 0).toLocaleString()}
              sub={`${(overview?.quiz_attempts ?? 0).toLocaleString()} all time`}
            />
            <HeroStat
              label="AI spend · 7d"
              value={overview?.cost_week_usd == null ? "—" : `$${overview.cost_week_usd.toFixed(2)}`}
            />
          </div>
        </div>

        <div className="mb-6 flex gap-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium ${
                tab === t.id
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        <div>
          {loading ? (
            <LoadingState text="Loading admin…" />
          ) : error ? (
            <div className="max-w-2xl">
              <ErrorBox message={error} onRetry={() => void load()} />
              {error.startsWith("Forbidden") && (
                <p className="mt-3 flex items-center gap-1.5 text-sm text-slate-500">
                  <ShieldAlert size={16} /> This area requires an admin account.
                </p>
              )}
            </div>
          ) : tab === "activity" ? (
            <ActivityPanel />
          ) : tab === "ai-usage" ? (
            <AIUsagePanel />
          ) : tab === "health" ? (
            <HealthPanel />
          ) : (
            <>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">Catalog</h2>
              <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatTile label="Spaces" value={overview?.spaces ?? 0} icon={<BookOpenText size={16} />} />
                <StatTile label="Projects" value={overview?.projects ?? 0} icon={<FolderOpen size={16} />} />
                <StatTile label="Documents" value={overview?.materials ?? 0} icon={<FileUp size={16} />} />
                <StatTile label="Quizzes" value={overview?.quizzes ?? 0} icon={<BrainCircuit size={16} />} />
              </div>

              <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">Engagement</h2>
              <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatTile label="Users" value={overview?.users ?? 0} icon={<Users size={16} />} />
                <StatTile label="Quiz Attempts" value={overview?.quiz_attempts ?? 0} icon={<HelpCircle size={16} />} />
                <StatTile label="Evidence Rows" value={overview?.evidence_rows ?? 0} icon={<CreditCard size={16} />} />
                <StatTile label="Recommendations" value={overview?.recommendations ?? 0} icon={<MessageCircle size={16} />} />
              </div>

              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-6 py-4">
                  <h2 className="text-sm font-semibold text-slate-800">
                    Users
                    {usersPage && (
                      <span className="ml-2 font-normal text-slate-400">
                        {(usersPage.total ?? 0).toLocaleString()}
                      </span>
                    )}
                  </h2>
                  <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 focus-within:border-indigo-400 focus-within:bg-white">
                    <Search size={14} className="text-slate-400" />
                    <input
                      value={userSearch}
                      onChange={(e) => {
                        setUserSearch(e.target.value)
                        setUserOffset(0)
                      }}
                      placeholder="Search email…"
                      className="w-44 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
                    />
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">User</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Projects</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Last active</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Role</th>
                        <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Journey</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(usersPage?.items ?? []).map((u, i) => (
                        <tr
                          key={u.id}
                          onClick={() => setJourneyUserId(u.id)}
                          className={`cursor-pointer border-b border-slate-50 transition-colors hover:bg-indigo-50/40 ${i === (usersPage?.items ?? []).length - 1 ? "border-0" : ""}`}
                        >
                          <td className="px-6 py-3.5">
                            <div className="flex items-center gap-3">
                              <Avatar email={u.email} className="h-8 w-8 text-xs" />
                              <div>
                                <div className="font-medium text-slate-800">{u.email.split("@")[0]}</div>
                                <div className="text-xs text-slate-400">{u.email}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 font-mono-data font-bold text-slate-900">
                            {u.project_count ?? 0}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3.5 text-xs text-slate-500" title={u.last_active ? new Date(u.last_active).toLocaleString() : undefined}>
                            {timeAgo(u.last_active)}
                          </td>
                          <td className="px-4 py-3.5">
                            {u.is_admin ? (
                              <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-medium text-white">Admin</span>
                            ) : (
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Student</span>
                            )}
                          </td>
                          <td className="px-6 py-3.5 text-right">
                            <span className="inline-flex rounded p-1.5 text-slate-400">
                              <Eye size={15} />
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {usersPage && (usersPage.total ?? 0) > (usersPage.limit ?? USERS_LIMIT) && (
                  <div className="flex items-center gap-3 border-t border-slate-100 px-6 py-3 text-sm text-slate-500">
                    <span>
                      {(usersPage.offset ?? 0) + 1}–{(usersPage.offset ?? 0) + usersPage.items.length} of{" "}
                      {(usersPage.total ?? 0).toLocaleString()}
                    </span>
                    <button
                      type="button"
                      disabled={userOffset === 0}
                      onClick={() => setUserOffset(Math.max(0, userOffset - USERS_LIMIT))}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-slate-700 disabled:opacity-40"
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      disabled={userOffset + USERS_LIMIT >= (usersPage.total ?? 0)}
                      onClick={() => setUserOffset(userOffset + USERS_LIMIT)}
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
      </div>

      {/* Learner journey slide-over */}
      {journeyUserId && (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setJourneyUserId(null)} />
          <div className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col bg-slate-50 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
              <h2 className="text-sm font-semibold text-slate-800">Learning journey</h2>
              <button
                type="button"
                onClick={() => setJourneyUserId(null)}
                aria-label="Close journey"
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-6">
              <JourneyPanel userId={journeyUserId} onBack={() => setJourneyUserId(null)} />
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
