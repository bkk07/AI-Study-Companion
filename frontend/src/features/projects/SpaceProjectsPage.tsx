import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { Brain, ChevronRight, Clock, GraduationCap, Plus } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Button, EmptyState, ErrorBox, Input, LoadingState } from "@/components/ui"
import { colorFor } from "@/features/spaces/SpacesPage"

type Space = { id: string; name: string }
type Project = { id: string; name: string; space_id: string; created_at: string }

export function SpaceProjectsPage() {
  const { spaceId } = useParams<{ spaceId: string }>()
  const [space, setSpace] = useState<Space | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spaceId])

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!spaceId || !name.trim()) return
    setCreating(true)
    setError(null)
    try {
      await apiClient.post(`/spaces/${spaceId}/projects`, { name: name.trim() })
      setName("")
      const res = await apiClient.get<Project[]>(`/spaces/${spaceId}/projects`)
      setProjects(res.data)
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to create project")
    } finally {
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl bg-slate-50 px-8 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <div className="mb-1 text-xs uppercase tracking-wider text-slate-400">{space?.name ?? "Space"}</div>
            <h1 className="text-2xl font-semibold text-slate-900">Projects</h1>
            <p className="mt-0.5 text-sm text-slate-500">Each project is a focused learning workspace for a subject</p>
          </div>
        </div>

        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
          <form onSubmit={onCreate} className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="New project — e.g. Chapter 3: Eigenvalues"
              aria-label="New project name"
            />
            <Button type="submit" disabled={creating || !name.trim()} className="shrink-0">
              <Plus size={15} />
              {creating ? "Creating…" : "New Project"}
            </Button>
          </form>
        </div>

        <div>
          {loading ? (
            <LoadingState text="Loading projects…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void fetchAll()} />
          ) : projects.length === 0 ? (
            <EmptyState
              icon={<Brain size={24} />}
              title="No projects yet"
              hint="Create a project to start uploading your study material and building your knowledge map."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {projects.map((p) => (
                <Link
                  key={p.id}
                  to={`/spaces/${spaceId}/projects/${p.id}?tab=overview`}
                  className="group cursor-pointer rounded-xl border border-slate-200 bg-white p-6 transition-all hover:border-slate-300 hover:shadow-sm"
                >
                  <div className="mb-4 flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-xl text-sm font-bold text-white"
                        style={{ backgroundColor: colorFor(p.id) }}
                      >
                        {p.name.trim()[0]?.toUpperCase() ?? <GraduationCap size={18} />}
                      </div>
                      <h3 className="text-base font-semibold text-slate-900 transition-colors group-hover:text-indigo-700">
                        {p.name}
                      </h3>
                    </div>
                    <ChevronRight size={16} className="mt-0.5 shrink-0 text-slate-300 transition-colors group-hover:text-indigo-400" />
                  </div>
                  <div className="mt-3 flex items-center gap-1 border-t border-slate-100 pt-4 text-xs text-slate-400">
                    <Clock size={11} />
                    Created {new Date(p.created_at).toLocaleDateString()}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
