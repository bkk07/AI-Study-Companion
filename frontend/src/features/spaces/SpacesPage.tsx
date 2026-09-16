import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Clock, FolderOpen, Layers, MoreHorizontal, Plus } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Button, EmptyState, ErrorBox, Input, LoadingState, SectionHeader } from "@/components/ui"

type Space = { id: string; name: string; created_at: string }

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

export function SpacesPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  const fetchSpaces = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<Space[]>("/spaces")
      setSpaces(res.data)
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to load spaces")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSpaces()
  }, [])

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setFieldError("Give your space a name first")
      return
    }
    setFieldError(null)
    setCreating(true)
    setError(null)
    try {
      await apiClient.post("/spaces", { name: name.trim() })
      setName("")
      await fetchSpaces()
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to create space")
    } finally {
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl bg-slate-50 px-8 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Your Spaces</h1>
            <p className="mt-0.5 text-sm text-slate-500">Organize your learning into subject areas</p>
          </div>
        </div>

        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
          <form onSubmit={onCreate} className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="New space name — e.g. Linear Algebra"
              aria-label="New space name"
            />
            {fieldError && <p className="text-sm font-medium text-red-600 sm:hidden">{fieldError}</p>}
            <Button type="submit" disabled={creating} className="shrink-0">
              <Plus size={15} />
              {creating ? "Creating…" : "New Space"}
            </Button>
          </form>
          {fieldError && <p className="mt-2 hidden text-sm font-medium text-red-600 sm:block">{fieldError}</p>}
        </div>

        <div>
          {loading ? (
            <LoadingState text="Loading spaces…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void fetchSpaces()} />
          ) : spaces.length === 0 ? (
            <EmptyState
              icon={<Layers size={24} />}
              title="No spaces yet"
              hint="Create your first space to organize your learning into subject areas."
            />
          ) : (
            <div className="grid gap-4">
              {spaces.map((s) => (
                <Link
                  key={s.id}
                  to={`/spaces/${s.id}`}
                  className="group cursor-pointer rounded-xl border border-slate-200 bg-white p-6 transition-all hover:border-slate-300 hover:shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                        style={{ backgroundColor: `${colorFor(s.id)}18`, color: colorFor(s.id) }}
                      >
                        <FolderOpen size={18} />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 transition-colors group-hover:text-indigo-700">
                          {s.name}
                        </h3>
                        <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
                          <span className="flex items-center gap-1">
                            <Clock size={12} />
                            Created {new Date(s.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                      <span className="rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600">
                        Open
                      </span>
                      <span className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
                        <MoreHorizontal size={15} />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="mt-10">
          <SectionHeader title="How spaces work" subtitle="One space per subject. Inside each: projects, PDFs, tutor chats, and quizzes." />
        </div>
      </div>
    </AppShell>
  )
}
