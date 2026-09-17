import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  ArrowRight,
  CalendarCheck,
  Flame,
  FolderKanban,
  Inbox,
  MessagesSquare,
  Sparkles,
  TriangleAlert,
  Wand2,
  Zap,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { useAuth } from "@/context/AuthContext"
import { ErrorBox, LoadingState, SectionHeader, StatCard } from "@/components/ui"
import { tileFor } from "@/features/spaces/SpacesPage"
import { timeAgo } from "@/features/admin/format"
import type { HomeRead } from "@/features/home/types"

const ACTION_TABS: Record<string, string> = {
  ask_tutor: "tutor",
  targeted_quiz: "quiz",
  explain_back: "open-ended",
  review_material: "materials",
  exam_mode: "quiz",
}

function actionTab(action: string): string {
  return ACTION_TABS[action] ?? "overview"
}

function projectLink(spaceId: string, projectId: string, tab: string): string {
  return `/spaces/${spaceId}/projects/${projectId}?tab=${tab}`
}

function ProgressRing({ pct }: { pct: number | null }) {
  const r = 15.5
  const c = 2 * Math.PI * r
  const filled = pct === null ? 0 : Math.min(100, Math.max(0, pct))
  return (
    <span className="relative inline-flex h-10 w-10 items-center justify-center" title={pct === null ? "No evidence yet" : `${filled}% mastered`}>
      <svg viewBox="0 0 36 36" className="h-10 w-10 -rotate-90">
        <circle cx="18" cy="18" r={r} fill="none" strokeWidth="4" className="stroke-slate-100" />
        <circle
          cx="18"
          cy="18"
          r={r}
          fill="none"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${(filled / 100) * c} ${c}`}
          className="stroke-indigo-600"
        />
      </svg>
      <span className="font-mono-data absolute text-[10px] font-bold text-slate-800">
        {pct === null ? "—" : Math.round(filled)}
      </span>
    </span>
  )
}

function WeekSpark({ days }: { days: HomeRead["week_activity"] }) {
  const max = Math.max(1, ...days.map((d) => d.events))
  return (
    <div className="flex h-16 items-end gap-1.5" aria-label="Activity this week">
      {days.map((d) => (
        <div
          key={d.day}
          title={`${d.day}: ${d.events} events`}
          className={`flex-1 rounded-sm ${d.events > 0 ? "bg-indigo-500" : "bg-slate-100"}`}
          style={{ height: `${Math.max(8, (d.events / max) * 100)}%` }}
        />
      ))}
    </div>
  )
}

export function HomeDashboard() {
  const { user } = useAuth()
  const [home, setHome] = useState<HomeRead | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<HomeRead>("/me/home")
      setHome(res.data)
    } catch (e: unknown) {
      const { message } = apiError(e)
      setError(message ?? "Failed to load your home.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return (
      <div className="bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <LoadingState text="Loading your home…" />
        </div>
      </div>
    )
  }

  if (error || !home) {
    return (
      <div className="bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <ErrorBox message={error ?? "Failed to load your home."} onRetry={() => void load()} />
        </div>
      </div>
    )
  }

  const isNew = home.recent_projects.length === 0 && home.stats.evidence_total === 0
  const firstName = user?.email.split("@")[0] ?? "there"

  // Brand-new users keep the classic starter cards as the zero state.
  if (isNew) {
    const cards = [
      {
        to: "/spaces",
        icon: FolderKanban,
        title: "My spaces",
        text: "Organize subjects into spaces, then projects. Pick up exactly where you left off.",
      },
      {
        to: "/spaces",
        icon: MessagesSquare,
        title: "Ask the tutor",
        text: "Open any project and chat with your materials — answers cite your uploads.",
      },
      {
        to: "/spaces",
        icon: Wand2,
        title: "Quiz yourself",
        text: "Generate adaptive quizzes tuned to your weakest concepts.",
      },
    ]
    return (
      <div className="bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <SectionHeader
            title={`Welcome${user ? `, ${firstName}` : ""}`}
            subtitle="Set up your first subject to start your learning loop."
          />
          <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((c) => (
              <Link key={c.title} to={c.to}>
                <div className="group h-full rounded-xl border border-slate-200 bg-white p-6 transition-all hover:border-slate-300 hover:shadow-sm">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <c.icon size={18} />
                  </span>
                  <h3 className="mt-4 flex items-center gap-1.5 text-base font-semibold text-slate-900">
                    {c.title}
                    <ArrowRight size={14} className="text-indigo-500 transition-transform group-hover:translate-x-1" />
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{c.text}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-5xl px-8 py-10">
        <SectionHeader
          title={`Welcome back, ${firstName}`}
          subtitle={
            home.stats.streak_days > 1
              ? `${home.stats.streak_days}-day streak — keep it burning.`
              : "Pick up where you left off."
          }
        />

        {/* Continue learning hero */}
        {home.continue && (
          <Link
            to={projectLink(home.continue.space_id, home.continue.project_id, home.continue.tab)}
            className={`group relative mb-6 block overflow-hidden rounded-2xl bg-gradient-to-br px-6 py-6 text-white shadow-sm transition-shadow hover:shadow-md ${tileFor(home.continue.project_id)}`}
          >
            <div
              className="pointer-events-none absolute -right-10 -top-14 h-48 w-48 rounded-full bg-white/10"
              aria-hidden
            />
            <div className="relative flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-white/70">
                  <Zap size={13} /> Continue learning
                </div>
                <div className="mt-1 truncate text-xl font-semibold tracking-tight">
                  {home.continue.project_name}
                </div>
                <div className="mt-0.5 text-sm text-white/75">
                  {home.continue.space_name} · touched {timeAgo(home.continue.touched_at)}
                </div>
              </div>
              <span className="flex shrink-0 items-center gap-1 rounded-lg bg-white/20 px-4 py-2 text-sm font-semibold ring-1 ring-white/30 transition-transform group-hover:translate-x-1">
                Resume <ArrowRight size={15} />
              </span>
            </div>
          </Link>
        )}

        {/* Stats + week activity */}
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            label="Day streak"
            value={home.stats.streak_days}
            icon={<Flame size={18} />}
            accent="amber"
            sub={home.stats.streak_days > 1 ? "evidence logged daily" : "log evidence to start"}
          />
          <StatCard
            label="Reviews due"
            value={home.stats.due_total}
            icon={<CalendarCheck size={18} />}
            accent="indigo"
          />
          <div className="space-y-3 rounded-xl border border-slate-100 bg-white p-5">
            <WeekSpark days={home.week_activity} />
            <div>
              <div className="font-mono-data text-2xl font-bold text-slate-900">{home.stats.events_week}</div>
              <div className="mt-0.5 text-sm text-slate-500">Events this week</div>
            </div>
          </div>
          <StatCard
            label="Evidence banked"
            value={home.stats.evidence_total}
            icon={<Sparkles size={18} />}
            accent="green"
          />
        </div>

        {/* Next actions */}
        {home.next_actions.length > 0 && (
          <div className="mb-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="text-sm font-semibold text-slate-800">What should you do next?</h2>
            </div>
            <ul>
              {home.next_actions.map((a) => (
                <li key={`${a.project_id}-${a.action_type}-${a.concept_id ?? "none"}`} className="border-b border-slate-50 last:border-0">
                  <Link
                    to={projectLink(a.space_id, a.project_id, actionTab(a.action_type))}
                    className="group flex items-center gap-4 px-6 py-4 transition-colors hover:bg-indigo-50/40"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-xs font-bold text-indigo-700">
                      {a.concept_title?.trim()[0]?.toUpperCase() ?? "•"}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-slate-800">
                        {a.action_type.replace(/_/g, " ")}
                        {a.concept_title ? ` · ${a.concept_title}` : ""}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {a.project_name} — {a.reasoning}
                      </span>
                    </span>
                    <ArrowRight size={15} className="shrink-0 text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-500" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Attention inbox */}
        {home.attention.length > 0 && (
          <div className="mb-6 overflow-hidden rounded-xl border border-rose-100 bg-white">
            <div className="border-b border-rose-50 bg-rose-50/50 px-6 py-4">
              <h2 className="flex items-center gap-1.5 text-sm font-semibold text-rose-900">
                <TriangleAlert size={15} /> Needs attention
              </h2>
            </div>
            <ul>
              {home.attention.map((a) => (
                <li key={`${a.project_id}-${a.concept_id}`} className="border-b border-slate-50 last:border-0">
                  <Link
                    to={projectLink(a.space_id, a.project_id, "progress")}
                    className="group flex items-center gap-4 px-6 py-4 transition-colors hover:bg-rose-50/50"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-slate-800">
                        {a.concept_title}
                        <span className="ml-2 rounded-full bg-rose-100 px-2 py-0.5 font-mono text-[11px] font-medium text-rose-700">
                          {a.mismatch_type}
                        </span>
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {a.project_name} — {a.reason}
                      </span>
                    </span>
                    <ArrowRight size={15} className="shrink-0 text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-rose-500" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recent projects */}
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Recent projects</h2>
          <Link to="/spaces" className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:underline">
            <Inbox size={14} /> All spaces
          </Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {home.recent_projects.map((p) => (
            <Link
              key={p.id}
              to={projectLink(p.space_id, p.id, "overview")}
              className="group overflow-hidden rounded-2xl border border-slate-200 bg-white transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
            >
              <div className="flex items-center gap-4 px-5 py-4">
                <ProgressRing pct={p.progress_pct} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-base font-semibold text-slate-900 group-hover:text-indigo-700">
                    {p.name}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-400">
                    <span>{p.space_name}</span>
                    {p.due_count > 0 && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-700">
                        {p.due_count} due
                      </span>
                    )}
                    {p.attention_count > 0 && (
                      <span className="rounded-full bg-rose-100 px-2 py-0.5 font-semibold text-rose-700">
                        {p.attention_count} needs attention
                      </span>
                    )}
                    {p.touched_at && <span>{timeAgo(p.touched_at)}</span>}
                  </div>
                </div>
                <ArrowRight size={15} className="shrink-0 text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-500" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
