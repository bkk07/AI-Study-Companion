import { useEffect, useState } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import { ChevronLeft } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { ErrorBox, LoadingState } from "@/components/ui"
import { Dashboard } from "@/features/dashboard/Dashboard"
import { Flashcards } from "@/features/flashcards/Flashcards"
import { AnalyticsView } from "@/features/analytics/AnalyticsView"
import { GrowthView } from "@/features/analytics/GrowthView"
import { ProgressMap } from "@/features/progress/ProgressMap"
import { StructureView } from "@/features/structure/StructureView"
import { QuizTaker } from "@/features/quiz/QuizTaker"
import { TutorChat } from "@/features/tutor/TutorChat"
import { MaterialsPanel } from "@/features/projects/MaterialsPanel"
import { colorFor } from "@/features/spaces/SpacesPage"
import { cn } from "@/lib/utils"

type Project = { id: string; name: string; space_id: string; created_at: string }
type Space = { id: string; name: string }

type TabId = "overview" | "tutor" | "quiz" | "flashcards" | "materials" | "structure" | "progress"

const VALID_TABS: TabId[] = ["overview", "tutor", "quiz", "flashcards", "materials", "structure", "progress"]

export function ProjectDetailPage() {
  const { spaceId, projectId } = useParams<{ spaceId: string; projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab") as TabId | null
  const tab: TabId = rawTab && VALID_TABS.includes(rawTab) ? rawTab : "overview"
  const setTab = (t: TabId) => setSearchParams({ tab: t }, { replace: false })

  const [project, setProject] = useState<Project | null>(null)
  const [space, setSpace] = useState<Space | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    Promise.all([
      apiClient.get<Project>(`/projects/${projectId}`),
      spaceId ? apiClient.get<Space>(`/spaces/${spaceId}`).then((r) => r.data).catch(() => null) : Promise.resolve(null),
    ])
      .then(([projRes, spaceData]) => {
        setProject(projRes.data)
        if (spaceData) setSpace(spaceData as Space)
      })
      .catch((e: unknown) => {
        const { status, message: detail } = apiError(e)
        if (status === 404) setError("Project not found or not owned by you.")
        else setError(detail ?? "Failed to load project")
      })
      .finally(() => setLoading(false))
  }, [projectId, spaceId])

  return (
    <AppShell wide>
      <div className="min-h-full bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <Link
            to={spaceId ? `/spaces/${spaceId}` : "/spaces"}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600"
          >
            <ChevronLeft size={12} />
            {space?.name ?? "Back to space"}
          </Link>

          {loading ? (
            <LoadingState text="Opening project…" />
          ) : error ? (
            <div className="mt-4 max-w-2xl">
              <ErrorBox message={error} />
            </div>
          ) : project ? (
            <div>
              <div className="mt-2">
                <div className="text-xs uppercase tracking-wider text-slate-400">{space?.name ?? "Project"}</div>
                <h1 className="font-display mt-1 flex items-center gap-3 text-2xl font-semibold text-slate-900">
                  <span
                    className="flex h-10 w-10 items-center justify-center rounded-xl text-sm font-bold text-white"
                    style={{ backgroundColor: colorFor(project.id) }}
                  >
                    {project.name.trim()[0]?.toUpperCase() ?? "?"}
                  </span>
                  {project.name}
                </h1>
                <p className="mt-0.5 text-sm text-slate-500">
                  Studying since {new Date(project.created_at).toLocaleDateString()} · everything here is scoped to this project.
                </p>
              </div>

              <div className="mt-6 flex gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 lg:hidden">
                {VALID_TABS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTab(t)}
                    className={cn(
                      "shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition-colors",
                      tab === t ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100",
                    )}
                  >
                    {t === "materials" ? "Documents" : t === "structure" ? "Structure" : t}
                  </button>
                ))}
              </div>

              <div key={tab} className="mt-6">
                {tab === "overview" && projectId && <Dashboard projectId={projectId} overviewMode />}
                {tab === "tutor" && projectId && <TutorChat projectId={projectId} />}
                {tab === "quiz" && projectId && <QuizTaker projectId={projectId} />}
                {tab === "flashcards" && projectId && <Flashcards projectId={projectId} />}
                {tab === "materials" && projectId && <MaterialsPanel projectId={projectId} />}
                {tab === "structure" && projectId && <StructureView projectId={projectId} />}
                {tab === "progress" && projectId && (
                  <div className="space-y-8">
                    <ProgressMap projectId={projectId} />
                    <GrowthView projectId={projectId} />
                    <AnalyticsView projectId={projectId} />
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  )
}
