import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowRight, Brain, Clock, GraduationCap, Plus, Target } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Button, ErrorBox, Input, LoadingState } from "@/components/ui"
import { colorFor, tileFor } from "@/features/spaces/SpacesPage"
import { timeAgo } from "@/features/admin/format"

type Space = { id: string; name: string; description: string | null }
type Project = { id: string; name: string; space_id: string; description: string | null; goal: string | null; created_at: string }

const NAME_MAX = 80

export function SpaceProjectsPage() {
  const { spaceId } = useParams<{ spaceId: string }>()
  const [space, setSpace] = useState<Space | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [goal, setGoal] = useState("")
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  const fetchAll = async () => {
    if (!spaceId) return
    setLoading(true)
    setError(null)
    try {
      const [spaceRes, projRes] = await Promise.all([
        apiClient.get<Space>(`/spaces/${spaceId}`),
        apiClient.get<Project[]>(`/spaces/${spaceId}/projects`),
      ])
      setSpace(spaceRes.data)
      setProjects(projRes.data)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 404) setError("Space not found or not owned by you.")
      else setError(detail ?? "Failed to load space/projects")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spaceId])

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
    setGoal("")
    setFieldError(null)
    setModalOpen(true)
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!spaceId) return
    if (!name.trim()) {
      setFieldError("Give your project a name first")
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
      await apiClient.post(`/spaces/${spaceId}/projects`, {
        name: name.trim(),
        description: description.trim() || null,
        goal: goal.trim() || null,
      })
      setModalOpen(false)
      const res = await apiClient.get<Project[]>(`/spaces/${spaceId}/projects`)
      setProjects(res.data)
    } catch (err: unknown) {
      setFieldError(apiError(err).message ?? "Failed to create project")
    } finally {
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-8 py-10">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-slate-400">
              {space?.name ?? "Space"}
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Projects</h1>
            <p className="mt-0.5 text-sm text-slate-500">
              {space?.description || "Each project is a focused learning workspace for a subject"}
            </p>
          </div>
          <Button type="button" onClick={openModal} className="shrink-0">
            <Plus size={15} />
            New Project
          </Button>
        </div>

        <div>
          {loading ? (
            <LoadingState text="Loading projects…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void fetchAll()} />
          ) : projects.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-8 py-14 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                <Brain size={24} />
              </div>
              <h3 className="text-lg font-semibold text-slate-800">No projects yet</h3>
              <p className="mx-auto mt-1 max-w-xs text-sm text-slate-500">
                Create a project to start uploading your study material and building your knowledge map.
              </p>
              <Button type="button" onClick={openModal} className="mt-5">
                <Plus size={15} />
                Create your first project
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {projects.map((p) => (
                <Link
                  key={p.id}
                  to={`/spaces/${spaceId}/projects/${p.id}?tab=overview`}
                  className="group overflow-hidden rounded-2xl border border-slate-200 bg-white transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
                >
                  <div className={`relative bg-gradient-to-br px-5 pb-4 pt-5 ${tileFor(p.id)}`}>
                    <div
                      className="pointer-events-none absolute -right-6 -top-8 h-28 w-28 rounded-full bg-white/10"
                      aria-hidden
                    />
                    <div className="relative flex items-center gap-3">
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white ring-1 ring-white/30"
                        style={{ backgroundColor: `${colorFor(p.id)}cc` }}
                      >
                        {p.name.trim()[0]?.toUpperCase() ?? <GraduationCap size={18} />}
                      </div>
                      <h3 className="truncate text-lg font-semibold tracking-tight text-white">{p.name}</h3>
                    </div>
                  </div>
                  <div className="px-5 py-4">
                    {p.goal ? (
                      <p className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600">
                        <Target size={12} className="shrink-0" />
                        <span className="truncate">{p.goal}</span>
                      </p>
                    ) : (
                      <p className="min-h-4 text-xs italic text-slate-300">No learning goal set</p>
                    )}
                    {p.description ? (
                      <p className="mt-1.5 line-clamp-2 min-h-10 text-sm text-slate-500">{p.description}</p>
                    ) : (
                      <p className="mt-1.5 min-h-10 text-sm italic text-slate-300">No description</p>
                    )}
                    <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1" title={new Date(p.created_at).toLocaleString()}>
                        <Clock size={11} />
                        {timeAgo(p.created_at) === "just now" ? "Created just now" : `Created ${timeAgo(p.created_at)}`}
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
      </div>

      {/* Creation dialog */}
      {modalOpen && (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Create a new project">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => !creating && setModalOpen(false)} />
          <div className="absolute left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-2xl">
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">New project</h2>
            <p className="mt-0.5 text-sm text-slate-500">A focused workspace inside {space?.name ?? "this space"}.</p>
            <form onSubmit={onCreate} className="mt-4 space-y-3">
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label htmlFor="project-name" className="text-sm font-medium text-slate-700">
                    Name
                  </label>
                  <span className={`text-xs ${name.trim().length > NAME_MAX ? "font-semibold text-red-600" : "text-slate-400"}`}>
                    {name.trim().length}/{NAME_MAX}
                  </span>
                </div>
                <Input
                  id="project-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Chapter 3: Eigenvalues"
                  aria-label="New project name"
                  autoFocus
                  maxLength={NAME_MAX + 20}
                />
              </div>
              <div>
                <label htmlFor="project-desc" className="mb-1.5 block text-sm font-medium text-slate-700">
                  Description <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <Input
                  id="project-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Exam prep for the December paper"
                  aria-label="New project description"
                />
              </div>
              <div>
                <label htmlFor="project-goal" className="mb-1.5 block text-sm font-medium text-slate-700">
                  Learning goal <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <Input
                  id="project-goal"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="e.g. Master gradient descent and backpropagation"
                  aria-label="New project learning goal"
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
                  {creating ? "Creating…" : "Create project"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  )
}
