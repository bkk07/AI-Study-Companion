import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import apiClient from "@/lib/axios"

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
      const detail = (e as { response?: { data?: { detail?: string }; status?: number } }).response?.data?.detail
      const status = (e as { response?: { status?: number } }).response?.status
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
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Failed to create project"
      setError(msg)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="flex items-center gap-2 text-sm">
        <Link to="/spaces" className="text-primary hover:underline">
          Spaces
        </Link>
        <span className="text-muted-foreground">/</span>
        <span className="font-medium">{space?.name ?? spaceId?.slice(0, 8)}</span>
        <span className="ml-auto">
          <Link to="/" className="text-primary hover:underline">
            Home
          </Link>
        </span>
      </div>

      <h1 className="mt-4 text-2xl font-bold">{space ? space.name : "Space"}</h1>
      <p className="mt-1 text-sm text-muted-foreground">Projects live inside this space — hierarchy: user → space → project.</p>

      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

      <form onSubmit={onCreate} className="mt-6 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          className="flex h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <button
          type="submit"
          disabled={creating || !name.trim()}
          className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50"
        >
          {creating ? "Creating…" : "Create project"}
        </button>
      </form>

      <div className="mt-6 rounded-lg border bg-card">
        {loading ? (
          <p className="p-4 text-sm text-muted-foreground">Loading…</p>
        ) : projects.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">No projects yet — create one above.</p>
            <button onClick={fetchAll} className="mt-2 text-sm text-primary hover:underline">
              Retry
            </button>
          </div>
        ) : (
          <ul className="divide-y">
            {projects.map((p) => (
              <li key={p.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-muted-foreground">{new Date(p.created_at).toLocaleString()}</p>
                </div>
                <Link to={`/spaces/${spaceId}/projects/${p.id}`} className="text-sm text-primary hover:underline">
                  Open →
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
