import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowRight, ChevronRight, GraduationCap, Plus } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Button, Card, EmptyState, ErrorBox, Input, LoadingState, PageHeader } from "@/components/ui"
import { tileFor } from "@/features/spaces/SpacesPage"

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

  const tile = spaceId ? tileFor(spaceId) : "from-violet-500 to-purple-600"

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Link to="/spaces" className="font-semibold text-violet-700 hover:underline">
            Spaces
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="font-medium text-foreground">{space?.name ?? "Space"}</span>
        </nav>

        <div className="mt-4">
          <PageHeader
            eyebrow="Space"
            title={
              <span className="inline-flex items-center gap-3">
                <span className={`inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-soft ${tile}`}>
                  <GraduationCap className="h-6 w-6" />
                </span>
                {space?.name ?? "Loading…"}
              </span>
            }
            description="Projects are individual study goals — a chapter, an exam, a topic to master."
          />
        </div>

        <Card className="mt-6 p-4 sm:p-5">
          <form onSubmit={onCreate} className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="New project — e.g. Chapter 3: Eigenvalues"
              aria-label="New project name"
            />
            <Button type="submit" disabled={creating || !name.trim()} className="shrink-0 px-5">
              <Plus className="h-4 w-4" />
              {creating ? "Creating…" : "New project"}
            </Button>
          </form>
        </Card>

        <div className="mt-6">
          {loading ? (
            <LoadingState text="Loading projects…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void fetchAll()} />
          ) : projects.length === 0 ? (
            <EmptyState
              icon={<GraduationCap className="h-6 w-6" />}
              title="No projects yet"
              hint="Create one above — each project gets its own materials, tutor, quizzes, and mastery tracking."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((p, i) => (
                <Link key={p.id} to={`/spaces/${spaceId}/projects/${p.id}`}>
                  <Card
                    className="animate-fade-up stagger group h-full p-5 transition-all hover:-translate-y-1 hover:shadow-lift"
                    style={{ "--d": `${Math.min(i, 8) * 60}ms` } as React.CSSProperties}
                  >
                    <span className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br text-sm font-extrabold text-white shadow-soft ${tileFor(p.id)}`}>
                      {p.name.trim()[0]?.toUpperCase() ?? "?"}
                    </span>
                    <h3 className="mt-3 flex items-center gap-1.5 font-bold tracking-tight">
                      <span className="truncate">{p.name}</span>
                      <ArrowRight className="h-4 w-4 shrink-0 text-violet-500 transition-transform group-hover:translate-x-1" />
                    </h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Created {new Date(p.created_at).toLocaleDateString()}
                    </p>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
