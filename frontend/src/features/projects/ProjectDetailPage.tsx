import { useEffect, useState } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { ErrorBox, LoadingState } from "@/components/ui"
import { Dashboard, type ProjectTab } from "@/features/dashboard/Dashboard"
import { OverviewView } from "@/features/overview/OverviewView"
import { Flashcards } from "@/features/flashcards/Flashcards"
import { StructureView } from "@/features/structure/StructureView"
import { QuizTaker } from "@/features/quiz/QuizTaker"
import { TutorChat } from "@/features/tutor/TutorChat"
import { MaterialsPanel } from "@/features/projects/MaterialsPanel"
import { cn } from "@/lib/utils"

type Project = { id: string; name: string; space_id: string; created_at: string }

type TabId = "overview" | "tutor" | "quiz" | "flashcards" | "materials" | "structure" | "progress"

const VALID_TABS: TabId[] = ["overview", "tutor", "quiz", "flashcards", "materials", "structure", "progress"]

export function ProjectDetailPage() {
  const { projectId } = useParams<{ spaceId: string; projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab") as TabId | null
  const tab: TabId = rawTab && VALID_TABS.includes(rawTab) ? rawTab : "overview"
  const setTab = (t: TabId) => setSearchParams({ tab: t }, { replace: false })

  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [quizFocus, setQuizFocus] = useState<string | null>(null)

  const goTab = (t: ProjectTab) => {
    if (t === "quiz" || VALID_TABS.includes(t as TabId)) setTab(t as TabId)
  }

  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    // Ownership gate — children fetch their own scoped data.
    apiClient
      .get<Project>(`/projects/${projectId}`)
      .then((res) => setProject(res.data))
      .catch((e: unknown) => {
        const { status, message: detail } = apiError(e)
        if (status === 404) setError("Project not found or not owned by you.")
        else setError(detail ?? "Failed to load project")
      })
      .finally(() => setLoading(false))
  }, [projectId])

  return (
    <AppShell wide>
      <div className="min-h-full bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          {loading ? (
            <LoadingState text="Opening project…" />
          ) : error ? (
            <div className="mt-4 max-w-2xl">
              <ErrorBox message={error} />
            </div>
          ) : project ? (
            <div>
              <div className="flex gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 lg:hidden">
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
                {tab === "overview" && projectId && (
                  <OverviewView
                    projectId={projectId}
                    onNavigate={goTab}
                    onPracticeConcept={(id) => {
                      setQuizFocus(id)
                      setTab("quiz")
                    }}
                  />
                )}
                {tab === "tutor" && projectId && <TutorChat projectId={projectId} />}
                {tab === "quiz" && projectId && (
                  <QuizTaker
                    projectId={projectId}
                    focusConceptId={quizFocus}
                    onFocusConsumed={() => setQuizFocus(null)}
                  />
                )}
                {tab === "flashcards" && projectId && <Flashcards projectId={projectId} />}
                {tab === "materials" && projectId && <MaterialsPanel projectId={projectId} />}
                {tab === "structure" && projectId && <StructureView projectId={projectId} />}
                {tab === "progress" && projectId && (
                  <Dashboard
                    projectId={projectId}
                    onNavigate={goTab}
                    onPracticeConcept={(id) => {
                      setQuizFocus(id)
                      setTab("quiz")
                    }}
                  />
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  )
}
