import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Clock, FolderOpen, Layers, Plus, Upload, MessagesSquare, BarChart2 } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Button, ErrorBox, Input, LoadingState } from "@/components/ui"
import { timeAgo } from "@/features/admin/format"

type Space = { id: string; name: string; description: string | null; created_at: string }

const COLORS = ["#4f46e5", "#7c3aed", "#0891b2", "#059669", "#d97706", "#0284c7"]

export function colorFor(id: string): string {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return COLORS[h % COLORS.length]
}

export function tileFor(id: string): string {
  const map: Record<string, string> = {
    "#4f46e5": "from-indigo-500 to-indigo-600",
    "#7c3aed": "from-violet-500 to-purple-600",
    "#0891b2": "from-cyan-600 to-sky-600",
    "#059669": "from-emerald-500 to-teal-600",
    "#d97706": "from-amber-500 to-orange-600",
    "#0284c7": "from-sky-500 to-blue-600",
  }
  return map[colorFor(id)] ?? "from-indigo-500 to-indigo-600"
}

const NAME_MAX = 80

const STEPS = [
  { icon: <Layers size={16} />, title: "Create a space", text: "One space per subject — Maths, Biology, interview prep." },
  { icon: <Upload size={16} />, title: "Add projects & PDFs", text: "Upload material; it gets mapped into concepts." },
  { icon: <MessagesSquare size={16} />, title: "Chat & quiz", text: "Grounded tutor chats and adaptive quizzes." },
  { icon: <BarChart2 size={16} />, title: "Track mastery", text: "Evidence-based mastery per concept." },
]

export function SpacesPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  const fetchSpaces = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<Space[]>("/spaces")
      setSpaces(res.data)
      // Project counts enrich cards; best-effort — a failed count hides, never blocks.
      const settled = await Promise.allSettled(
        res.data.map(async (s) => {
          const r = await apiClient.get<unknown[]>(`/spaces/${s.id}/projects`)
          return [s.id, r.data.length] as const
        }),
      )
      const next: Record<string, number> = {}
      for (const r of settled) {
        if (r.status === "fulfilled") next[r.value[0]] = r.value[1]
      }
      setCounts(next)
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to load spaces")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchSpaces()
  }, [])

  // Esc closes the creation dialog.
  useEffect(() => {
    if (!modalOpen) return
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") setModalOpen(false)
    }
    window.addEventListener("keydown", h)
    return () => window.removeEventListener("keydown", h)
  }, [modalOpen])

  const openModal = () => {
    setName("")
    setDescription("")
    setFieldError(null)
    setModalOpen(true)
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setFieldError("Give your space a name first")
      return
    }
    if (name.trim().length > NAME_MAX) {
      setFieldError(`Keep it under ${NAME_MAX} characters`)
      return
    }
    setFieldError(null)
    setCreating(true)
    setError(null)
    try {
      await apiClient.post("/spaces", { name: name.trim(), description: description.trim() || null })
      setModalOpen(false)
      await fetchSpaces()
    } catch (err: unknown) {
      setFieldError(apiError(err).message ?? "Failed to create space")
    } finally {
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl px-8 py-10">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Your Spaces</h1>
            <p className="mt-0.5 text-sm text-slate-500">Organize your learning into subject areas</p>
          </div>
          <Button type="button" onClick={openModal} className="shrink-0">
            <Plus size={15} />
            New Space
          </Button>
        </div>

        <div>
          {loading ? (
            <LoadingState text="Loading spaces…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void fetchSpaces()} />
          ) : spaces.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-8 py-14 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                <Layers size={24} />
              </div>
              <h3 className="text-lg font-semibold text-slate-800">No spaces yet</h3>
              <p className="mx-auto mt-1 max-w-xs text-sm text-slate-500">
                Create your first space to organize projects, PDFs, tutor chats, and quizzes by subject.
              </p>
              <Button type="button" onClick={openModal} className="mt-5">
                <Plus size={15} />
                Create your first space
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {spaces.map((s) => (
                <Link
                  key={s.id}
                  to={`/spaces/${s.id}`}
                  className="group overflow-hidden rounded-2xl border border-slate-200 bg-white transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
                >
                  <div className={`relative bg-gradient-to-br px-5 pb-4 pt-5 ${tileFor(s.id)}`}>
                    <div
                      className="pointer-events-none absolute -right-6 -top-8 h-28 w-28 rounded-full bg-white/10"
                      aria-hidden
                    />
                    <div
                      className="pointer-events-none absolute right-10 top-6 h-12 w-12 rounded-full bg-white/10"
                      aria-hidden
                    />
                    <div className="relative flex items-start justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20 text-white ring-1 ring-white/30">
                        <FolderOpen size={18} />
                      </div>
                      {counts[s.id] !== undefined && (
                        <span className="rounded-full bg-black/20 px-2.5 py-1 text-xs font-semibold text-white ring-1 ring-white/20">
                          {counts[s.id]} {counts[s.id] === 1 ? "project" : "projects"}
                        </span>
                      )}
                    </div>
                    <h3 className="relative mt-3 truncate text-lg font-semibold tracking-tight text-white">
                      {s.name}
                    </h3>
                  </div>
                  <div className="px-5 py-4">
                    {s.description ? (
                      <p className="line-clamp-2 min-h-10 text-sm text-slate-500">{s.description}</p>
                    ) : (
                      <p className="min-h-10 text-sm italic text-slate-300">No description</p>
                    )}
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center gap-1" title={new Date(s.created_at).toLocaleString()}>
                        <Clock size={12} />
                        {timeAgo(s.created_at) === "just now" ? "Created just now" : `Created ${timeAgo(s.created_at)}`}
                      </span>
                      <span className="flex items-center gap-0.5 font-medium text-indigo-600 opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100">
                        Open <ArrowRight size={13} />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="mt-12">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">How spaces work</h2>
          <p className="mb-4 text-sm text-slate-500">One space per subject — from first upload to measured mastery.</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((st, i) => (
              <div key={st.title} className="relative rounded-xl border border-slate-200 bg-white p-4">
                <span className="font-mono-data absolute right-3 top-3 text-xs font-bold text-slate-200">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  {st.icon}
                </div>
                <div className="text-sm font-semibold text-slate-800">{st.title}</div>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">{st.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Creation dialog */}
      {modalOpen && (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Create a new space">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => !creating && setModalOpen(false)} />
          <div className="absolute left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-2xl">
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">New space</h2>
            <p className="mt-0.5 text-sm text-slate-500">A subject area to hold projects and materials.</p>
            <form onSubmit={onCreate} className="mt-4 space-y-3">
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label htmlFor="space-name" className="text-sm font-medium text-slate-700">
                    Name
                  </label>
                  <span className={`text-xs ${name.trim().length > NAME_MAX ? "font-semibold text-red-600" : "text-slate-400"}`}>
                    {name.trim().length}/{NAME_MAX}
                  </span>
                </div>
                <Input
                  id="space-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Linear Algebra"
                  aria-label="New space name"
                  autoFocus
                  maxLength={NAME_MAX + 20}
                />
              </div>
              <div>
                <label htmlFor="space-desc" className="mb-1.5 block text-sm font-medium text-slate-700">
                  Description <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <Input
                  id="space-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Maths minor, semester 2"
                  aria-label="New space description"
                />
              </div>
              {fieldError && (
                <p role="alert" className="text-sm font-medium text-red-600">
                  {fieldError}
                </p>
              )}
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  disabled={creating}
                  onClick={() => setModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-50"
                >
                  Cancel
                </button>
                <Button type="submit" disabled={creating}>
                  <Plus size={15} />
                  {creating ? "Creating…" : "Create space"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  )
}
