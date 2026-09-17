import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom"
import {
  BarChart2,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Dumbbell,
  FileText,
  Flame,
  HelpCircle,
  Layers,
  LayoutDashboard,
  LogOut,
  Map,
  MessageCircle,
  PenLine,
} from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { Logo } from "@/components/ui"
import { cn } from "@/lib/utils"
import apiClient from "@/lib/axios"

type TabId = "overview" | "tutor" | "quiz" | "flashcards" | "materials" | "structure" | "progress" | "practice" | "open-ended" | "analytics"

const PROJECT_NAV: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard size={16} /> },
  { id: "materials", label: "Documents", icon: <FileText size={16} /> },
  { id: "structure", label: "Structure", icon: <Map size={16} /> },
  { id: "tutor", label: "Tutor", icon: <MessageCircle size={16} /> },
  { id: "flashcards", label: "Flashcards", icon: <CreditCard size={16} /> },
  { id: "quiz", label: "Quiz", icon: <HelpCircle size={16} /> },
  { id: "practice", label: "Practice", icon: <Dumbbell size={16} /> },
  { id: "open-ended", label: "Open Ended Answers", icon: <PenLine size={16} /> },
  { id: "progress", label: "Dashboard", icon: <BarChart2 size={16} /> },
  { id: "analytics", label: "Analytics", icon: <Layers size={16} /> },
]

function StreakFlame() {
  const { token } = useAuth()
  const [streak, setStreak] = useState<number | null>(null)

  useEffect(() => {
    if (!token) {
      setStreak(null)
      return
    }
    let cancelled = false
    apiClient
      .get<{ streak_days: number }>("/me/streak")
      .then((r) => {
        if (!cancelled) setStreak(r.data.streak_days)
      })
      .catch(() => {
        if (!cancelled) setStreak(null)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  // No streak yet or still loading: stay invisible, never an error state.
  if (streak === null || streak < 1) return null
  return (
    <span
      title={`${streak}-day study streak — evidence logged every day`}
      className="flex items-center gap-1 rounded-full bg-orange-50 px-2.5 py-1 text-xs font-bold text-orange-600 ring-1 ring-inset ring-orange-200"
    >
      <Flame size={13} className="fill-orange-200" />
      {streak}
    </span>
  )
}

export function AppShell({ children }: { children: React.ReactNode; wide?: boolean }) {
  const { user, token, logout } = useAuth()
  const nav = useNavigate()
  const location = useLocation()
  const { spaceId, projectId } = useParams<{ spaceId: string; projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [collapsed, setCollapsed] = useState(false)
  const [spaceName, setSpaceName] = useState<string | null>(null)

  const inProject = Boolean(spaceId && projectId)
  const activeTab = (searchParams.get("tab") as TabId | null) ?? "overview"
  // Admins get a minimal shell: admin content + sign out only. No spaces,
  // project nav, command palette, or collapse toggle.
  const isAdmin = user?.is_admin === true

  useEffect(() => {
    if (!spaceId || !token) {
      setSpaceName(null)
      return
    }
    let cancelled = false
    apiClient
      .get<{ name: string }>(`/spaces/${spaceId}`)
      .then((r) => {
        if (!cancelled) setSpaceName(r.data.name)
      })
      .catch(() => {
        if (!cancelled) setSpaceName(null)
      })
    return () => {
      cancelled = true
    }
  }, [spaceId, token])

  if (!token) {
    return (
      <div className="flex min-h-screen flex-col bg-slate-50">
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
            <Link to="/" aria-label="Home">
              <Logo />
            </Link>
            <nav className="flex items-center gap-2">
              <Link
                to="/login"
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Start free
              </Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-5 text-xs text-slate-500 sm:flex-row sm:px-6">
            <span className="inline-flex items-center gap-1.5">
              <Logo compact />
              <span className="font-semibold text-slate-800">Study Companion</span> — learn anything faster.
            </span>
            <span>Your materials stay private to your projects · Answers cite your uploads</span>
          </div>
        </footer>
      </div>
    )
  }

  const goTab = (tab: TabId) => {
    if (!spaceId || !projectId) return
    setSearchParams({ tab }, { replace: false })
  }

  const breadcrumb = inProject
    ? [spaceName ?? "Space", "Project", PROJECT_NAV.find((n) => n.id === activeTab)?.label]
        .filter(Boolean)
        .join(" / ")
    : location.pathname.startsWith("/admin")
      ? "Admin"
      : location.pathname.startsWith("/spaces/")
        ? `${spaceName ?? "Space"} / Projects`
        : "Spaces"

  const initials = user?.email
    ? user.email.trim()[0]?.toUpperCase() ?? "U"
    : "U"

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <aside
        className={cn(
          "flex flex-shrink-0 flex-col border-r border-slate-200 bg-white transition-all duration-200",
          collapsed ? "w-16" : "w-60",
        )}
      >
        <div
          className={cn(
            "flex h-14 flex-shrink-0 items-center border-b border-slate-100 px-4",
            collapsed ? "justify-center" : "gap-2.5",
          )}
        >
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-600">
            <BookOpen size={14} className="text-white" />
          </div>
          {!collapsed && <span className="text-sm font-semibold text-slate-900">Study Companion</span>}
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {isAdmin ? null : !inProject ? (
            <div className="mb-3 space-y-0.5">
              <div
                className={cn("sidebar-item", location.pathname.startsWith("/spaces") && "active")}
                onClick={() => nav("/spaces")}
                title={collapsed ? "Spaces" : undefined}
              >
                <Layers size={16} className="shrink-0" />
                {!collapsed && <span>Spaces</span>}
              </div>
              {spaceId && (
                <div
                  className="sidebar-item"
                  onClick={() => nav(`/spaces/${spaceId}`)}
                  title={collapsed ? "Projects" : undefined}
                >
                  <LayoutDashboard size={16} className="shrink-0" />
                  {!collapsed && <span>{spaceName ?? "Projects"}</span>}
                </div>
              )}
            </div>
          ) : (
            <>
              {!collapsed && (
                <div className="px-3 pb-2 pt-1">
                  <button
                    type="button"
                    className="flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600"
                    onClick={() => spaceId && nav(`/spaces/${spaceId}`)}
                  >
                    <ChevronLeft size={12} />
                    <span className="truncate">{spaceName ?? "Back"}</span>
                  </button>
                </div>
              )}
              <div className="space-y-0.5">
                {PROJECT_NAV.map((item) => (
                  <div
                    key={item.id}
                    className={cn("sidebar-item", activeTab === item.id && "active")}
                    onClick={() => goTab(item.id)}
                    title={collapsed ? item.label : undefined}
                  >
                    <span className="shrink-0">{item.icon}</span>
                    {!collapsed && <span>{item.label}</span>}
                  </div>
                ))}
              </div>
            </>
          )}

        </nav>

        <div className="space-y-0.5 border-t border-slate-100 p-2">
          <div
            className="sidebar-item"
            onClick={() => {
              logout()
              nav("/login")
            }}
            title={collapsed ? "Sign out" : undefined}
          >
            <LogOut size={16} className="shrink-0" />
            {!collapsed && <span>Sign out</span>}
          </div>
          {!isAdmin && (
            <button type="button" className="sidebar-item w-full" onClick={() => setCollapsed((c) => !c)}>
              {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
              {!collapsed && <span className="text-xs">Collapse</span>}
            </button>
          )}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 flex-shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-6">
          <div className="flex-1 truncate text-sm font-medium text-slate-500">{breadcrumb}</div>
          {!isAdmin && <StreakFlame />}
          <div
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
            title={user?.email ?? "Account"}
          >
            {initials}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
