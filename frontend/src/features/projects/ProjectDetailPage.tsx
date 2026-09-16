import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  ArrowLeft,
  FileUp,
  Layers,
  LayoutDashboard,
  LineChart,
  MessagesSquare,
  Network,
  Wand2,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Card, ErrorBox, LoadingState, PageHeader } from "@/components/ui"
import { Dashboard } from "@/features/dashboard/Dashboard"
import { Flashcards } from "@/features/flashcards/Flashcards"
import { AnalyticsView } from "@/features/analytics/AnalyticsView"
import { GrowthView } from "@/features/analytics/GrowthView"
import { ProgressMapCard } from "@/features/progress/ProgressMap"
import { StructureView } from "@/features/structure/StructureView"
import { QuizTaker } from "@/features/quiz/QuizTaker"
import { TutorChat } from "@/features/tutor/TutorChat"
import { MaterialsPanel } from "@/features/projects/MaterialsPanel"
import { tileFor } from "@/features/spaces/SpacesPage"
import { cn } from "@/lib/utils"

type Project = { id: string; name: string; space_id: string; created_at: string }
type Space = { id: string; name: string }

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "tutor", label: "Tutor", icon: MessagesSquare },
  { id: "quiz", label: "Quiz", icon: Wand2 },
  { id: "flashcards", label: "Flashcards", icon: Layers },
  { id: "materials", label: "Materials", icon: FileUp },
  { id: "structure", label: "Map", icon: Network },
  { id: "progress", label: "Progress", icon: LineChart },
] as const

type TabId = (typeof TABS)[number]["id"]

export function ProjectDetailPage() {
  const { spaceId, projectId } = useParams<{ spaceId: string; projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [space, setSpace] = useState<Space | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabId>("overview")

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
        const { status, message: detail } = apiError(e)
        if (status === 404) setError("Project not found or not owned by you.")
        else setError(detail ?? "Failed to load project")
      })
      .finally(() => setLoading(false))
  }, [projectId, spaceId])

  return (
    <AppShell wide>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <Link
          to={spaceId ? `/spaces/${spaceId}` : "/spaces"}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted-foreground transition-colors hover:text-violet-700"
        >
          <ArrowLeft className="h-4 w-4" />
          {space?.name ?? "Back to space"}
        </Link>

        {loading ? (
          <LoadingState text="Opening project…" />
        ) : error ? (
          <div className="mt-4 max-w-2xl">
            <ErrorBox message={error} />
          </div>
        ) : project ? (
          <div className="animate-fade-up">
            <div className="mt-3">
              <PageHeader
                eyebrow={space?.name ?? "Project"}
                title={
                  <span className="inline-flex items-center gap-3">
                    <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-lg font-extrabold text-white shadow-soft ${tileFor(project.id)}`}>
                      {project.name.trim()[0]?.toUpperCase() ?? "?"}
                    </span>
                    {project.name}
                  </span>
                }
                description={`Studying since ${new Date(project.created_at).toLocaleDateString()} · everything here is scoped to this project.`}
              />
            </div>

            {/* Tab bar */}
            <div className="sticky top-16 z-30 -mx-4 mt-6 border-y border-white/50 bg-background/85 px-4 py-2.5 backdrop-blur-xl sm:-mx-6 sm:px-6">
              <div className="flex gap-1 overflow-x-auto">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTab(t.id)}
                    className={cn(
                      "inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-semibold transition-all",
                      tab === t.id
                        ? "bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-soft"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <t.icon className="h-4 w-4" />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div key={tab} className="animate-fade-up mt-5">
              {tab === "overview" && projectId && (
                <Card className="p-5 sm:p-6">
                  <Dashboard projectId={projectId} />
                </Card>
              )}
              {tab === "tutor" && projectId && (
                <Card className="p-5 sm:p-6">
                  <TutorChat projectId={projectId} />
                </Card>
              )}
              {tab === "quiz" && projectId && (
                <Card className="p-5 sm:p-6">
                  <QuizTaker projectId={projectId} />
                </Card>
              )}
              {tab === "flashcards" && projectId && (
                <Card className="p-5 sm:p-6">
                  <Flashcards projectId={projectId} />
                </Card>
              )}
              {tab === "materials" && projectId && <MaterialsPanel projectId={projectId} />}
              {tab === "structure" && projectId && (
                <Card className="p-5 sm:p-6">
                  <StructureView projectId={projectId} />
                </Card>
              )}
              {tab === "progress" && projectId && (
                <div className="space-y-4">
                  <ProgressMapCard projectId={projectId} />
                  <div className="grid gap-4 lg:grid-cols-2">
                  <Card className="p-5 sm:p-6">
                    <h3 className="font-bold">Growth</h3>
                    <GrowthView projectId={projectId} />
                  </Card>
                  <Card className="p-5 sm:p-6">
                    <h3 className="font-bold">Analytics</h3>
                    <AnalyticsView projectId={projectId} />
                  </Card>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  )
}
