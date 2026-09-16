import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import apiClient from "@/lib/axios"
import { Dashboard } from "@/features/dashboard/Dashboard"
import { StructureView } from "@/features/structure/StructureView"
import { QuizTaker } from "@/features/quiz/QuizTaker"
import { TutorChat } from "@/features/tutor/TutorChat"

type Project = { id: string; name: string; space_id: string; created_at: string }
type Space = { id: string; name: string }

export function ProjectDetailPage() {
  const { spaceId, projectId } = useParams<{ spaceId: string; projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [space, setSpace] = useState<Space | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    // Fetch via direct and nested for verification; both should succeed if owned
    Promise.all([
      apiClient.get<Project>(`/projects/${projectId}`),
      spaceId ? apiClient.get<Space>(`/spaces/${spaceId}`).then((r) => r.data).catch(() => null) : Promise.resolve(null),
    ])
      .then(([projRes, spaceData]) => {
        setProject(projRes.data)
        if (spaceData) setSpace(spaceData as Space)
      })
      .catch((e: unknown) => {
        const status = (e as { response?: { status?: number } }).response?.status
        const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        if (status === 404) setError("Project not found or not owned by you.")
        else setError(detail ?? "Failed to load project")
      })
      .finally(() => setLoading(false))
  }, [projectId, spaceId])

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="flex items-center gap-2 text-sm">
        <Link to="/spaces" className="text-primary hover:underline">
          Spaces
        </Link>
        <span className="text-muted-foreground">/</span>
        {spaceId ? (
          <Link to={`/spaces/${spaceId}`} className="text-primary hover:underline">
            {space?.name ?? spaceId.slice(0, 8)}
          </Link>
        ) : (
          <span>{space?.name ?? "Space"}</span>
        )}
        <span className="text-muted-foreground">/</span>
        <span className="font-medium">{project?.name ?? projectId?.slice(0, 8)}</span>
      </div>

      {loading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading…</p>
      ) : error ? (
        <div className="mt-6 rounded-md border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
          <Link to={spaceId ? `/spaces/${spaceId}` : "/spaces"} className="mt-2 inline-block text-sm text-primary hover:underline">
            Back
          </Link>
        </div>
      ) : project ? (
        <div className="mt-6 rounded-lg border bg-card p-6">
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">Hierarchy: user → space → project — verified via authorization dependency.</p>
          <p className="mt-2 text-xs text-muted-foreground">Project ID: {project.id}</p>
          <p className="text-xs text-muted-foreground">Space ID: {project.space_id}</p>
          <p className="text-xs text-muted-foreground">Created: {new Date(project.created_at).toLocaleString()}</p>
          <div className="mt-6 flex gap-4 text-sm">
            <Link to={`/spaces/${project.space_id}`} className="text-primary hover:underline">
              Back to space
            </Link>
            <Link to="/spaces" className="text-primary hover:underline">
              All spaces
            </Link>
          </div>
          <p className="mt-6 text-sm text-muted-foreground">Materials, chunks, and study features will attach to this project (Phases 18+).</p>
          <div className="mt-6 border-t pt-4">
            <h2 className="text-lg font-semibold">Learning structure</h2>
            {projectId ? <StructureView projectId={projectId} /> : null}
          </div>
          <div className="mt-6 border-t pt-4">
            <h2 className="text-lg font-semibold">Tutor</h2>
            {projectId ? <TutorChat projectId={projectId} /> : null}
          </div>
          <div className="mt-6 border-t pt-4">
            <h2 className="text-lg font-semibold">Quiz</h2>
            {projectId ? <QuizTaker projectId={projectId} /> : null}
          </div>
          <div className="mt-6 border-t pt-4">
            <h2 className="text-lg font-semibold">Mastery & recommendations</h2>
            {projectId ? <Dashboard projectId={projectId} /> : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
