import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom"
import {
  BarChart2,
  Bell,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Command,
  CreditCard,
  FileText,
  HelpCircle,
  Layers,
  LayoutDashboard,
  LogOut,
  Map,
  MessageCircle,
  Search,
} from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { Logo } from "@/components/ui"
import { cn } from "@/lib/utils"
import apiClient from "@/lib/axios"

type TabId = "overview" | "tutor" | "quiz" | "flashcards" | "materials" | "structure" | "progress"

const PROJECT_NAV: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard size={16} /> },
  { id: "materials", label: "Documents", icon: <FileText size={16} /> },
  { id: "structure", label: "Structure", icon: <Map size={16} /> },
  { id: "tutor", label: "Tutor", icon: <MessageCircle size={16} /> },
  { id: "flashcards", label: "Flashcards", icon: <CreditCard size={16} /> },
  { id: "quiz", label: "Quiz", icon: <HelpCircle size={16} /> },
  { id: "progress", label: "Dashboard", icon: <BarChart2 size={16} /> },
]

function NotifBell() {
  const [open, setOpen] = useState(false)
  const notifs = [
    { id: 1, text: "Flashcards due for review.", time: "Now" },
    { id: 2, text: "New recommendation ready in Overview.", time: "1h ago" },
    { id: 3, text: "Knowledge map updated from your latest PDF.", time: "2h ago" },
  ]
  return (
    <div className="relative">
      <button
        type="button"
        className="relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-slate-100"
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
      >
        <Bell size={16} className="text-slate-500" />
        <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-indigo-600" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <span className="text-sm font-semibold text-slate-800">Notifications</span>
            <button type="button" className="text-xs text-indigo-600 hover:underline" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          {notifs.map((n) => (
            <div key={n.id} className="cursor-pointer border-b border-slate-50 px-4 py-3 last:border-0 hover:bg-slate-50">
              <p className="text-sm text-slate-700">{n.text}</p>
              <p className="mt-0.5 text-xs text-slate-400">{n.time}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CommandPalette({ onClose }: { onClose: () => void }) {
  const nav = useNavigate()
  const { spaceId, projectId } = useParams<{ spaceId: string; projectId: string }>()
  const inProject = Boolean(spaceId && projectId)
  const base = inProject ? `/spaces/${spaceId}/projects/${projectId}` : null

  const actions = inProject && base
    ? [
        { label: "Ask Tutor", hint: "Grounded Q&A", tab: "tutor" as TabId },
        { label: "Start Quiz", hint: "Practice mode", tab: "quiz" as TabId },
        { label: "Review Flashcards", hint: "Due cards", tab: "flashcards" as TabId },
        { label: "View Knowledge Map", hint: "Topic tree", tab: "structure" as TabId },
        { label: "Upload Document", hint: "PDF library", tab: "materials" as TabId },
        { label: "View Dashboard", hint: "Progress", tab: "progress" as TabId },
      ]
    : [
        { label: "Go to Spaces", hint: "Library", tab: null },
        { label: "Open Admin", hint: "Overview", tab: null },
      ]

  const [q, setQ] = useState("")
  const filtered = actions.filter((a) => a.label.toLowerCase().includes(q.toLowerCase()))

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", h)
    return () => window.removeEventListener("keydown", h)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 pt-24" onClick={onClose}>
      <div
        className="mx-auto max-w-lg overflow-hidden rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Type a command…"
          className="w-full border-b border-slate-100 px-4 py-3 text-sm outline-none placeholder:text-slate-400"
        />
        <div className="max-h-80 overflow-y-auto p-2">
          {filtered.map((a) => (
            <button
              key={a.label}
              type="button"
              className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm hover:bg-slate-50"
              onClick={() => {
                if (a.tab && base) nav(`${base}?tab=${a.tab}`)
                else if (a.label.includes("Spaces")) nav("/spaces")
                else nav("/admin")
                onClose()
              }}
            >
              <span className="font-medium text-slate-800">{a.label}</span>
              <span className="text-xs text-slate-400">{a.hint}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-slate-400">No matching actions</p>
          )}
        </div>
        <div className="border-t border-slate-100 px-4 py-2 text-xs text-slate-400">
          ↑↓ navigate · ↵ select · Esc close
        </div>
      </div>
    </div>
  )
}

export function AppShell({ children }: { children: React.ReactNode; wide?: boolean }) {
  const { user, token, logout } = useAuth()
  const nav = useNavigate()
  const location = useLocation()
  const { spaceId, projectId } = useParams<{ spaceId: string; projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [collapsed, setCollapsed] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)
  const [spaceName, setSpaceName] = useState<string | null>(null)

  const inProject = Boolean(spaceId && projectId)
  const activeTab = (searchParams.get("tab") as TabId | null) ?? "overview"

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setCommandOpen(true)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])

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
          {!inProject ? (
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
          <div className="sidebar-item" onClick={() => setCommandOpen(true)} title={collapsed ? "Command" : undefined}>
            <Command size={16} className="shrink-0" />
            {!collapsed && <span>Command</span>}
          </div>
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
          <button type="button" className="sidebar-item w-full" onClick={() => setCollapsed((c) => !c)}>
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            {!collapsed && <span className="text-xs">Collapse</span>}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 flex-shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-6">
          <div className="flex-1 truncate text-sm font-medium text-slate-500">{breadcrumb}</div>
          <button
            type="button"
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-slate-100"
            onClick={() => setCommandOpen(true)}
          >
            <Search size={14} />
            <span className="hidden sm:inline">Search</span>
            <kbd className="font-mono-data ml-1 text-xs text-slate-400">⌘K</kbd>
          </button>
          <NotifBell />
          <div
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
            title={user?.email ?? "Account"}
          >
            {initials}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>

      {commandOpen && <CommandPalette onClose={() => setCommandOpen(false)} />}
    </div>
  )
}
