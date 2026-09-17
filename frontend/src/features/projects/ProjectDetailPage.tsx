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
import { QuizTaker, type DirectSession } from "@/features/quiz/QuizTaker"
import type { Card as FlashCard } from "@/features/flashcards/Flashcards"
import { TutorChat } from "@/features/tutor/TutorChat"
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage"
import { MaterialsPanel } from "@/features/projects/MaterialsPanel"
import { PracticePage } from "@/features/practice/PracticePage"
import { OpenEndedAnswersPage } from "@/features/openended/OpenEndedAnswersPage"
import { cn } from "@/lib/utils"

type Project = { id: string; name: string; space_id: string; created_at: string }

type TabId = "overview" | "tutor" | "quiz" | "flashcards" | "materials" | "structure" | "progress" | "practice" | "open-ended" | "analytics"

const VALID_TABS: TabId[] = ["overview", "tutor", "quiz", "flashcards", "materials", "structure", "progress", "practice", "open-ended", "analytics"]

const TAB_LABELS: Record<TabId, string> = {
  overview: "overview",
  tutor: "tutor",
  quiz: "quiz",
  flashcards: "flashcards",
  materials: "Documents",
  structure: "Structure",
  progress: "progress",
  practice: "practice",
  "open-ended": "Open Ended",
  analytics: "Analytics",
}

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
  const [quizDirect, setQuizDirect] = useState<DirectSession | null>(null)
  const [practiceDirect, setPracticeDirect] = useState<{ conceptIds: string[]; mcqCount: number; oeCount: number } | null>(null)
  const [flashcardsDirect, setFlashcardsDirect] = useState<{ cards: FlashCard[] } | null>(null)

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
        <div className={tab === "tutor" && project ? "px-3 pb-3 pt-3 sm:px-0 sm:pb-0 sm:pt-0" : "mx-auto max-w-5xl px-8 py-10"}>
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
                    {TAB_LABELS[t]}
                  </button>
                ))}
              </div>

              <div key={tab} className={tab === "tutor" ? "mt-3 sm:mt-0" : "mt-6"}>
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
                {tab === "tutor" && projectId && (
                  <TutorChat
                    projectId={projectId}
                    onQuizMe={() => setTab("quiz")}
                    onFlashcards={() => setTab("flashcards")}
                    onQuizReady={(s) => {
                      setQuizDirect(s)
                      setTab("quiz")
                    }}
                    onPracticeReady={(p) => {
                      setPracticeDirect(p)
                      setTab("practice")
                    }}
                    onFlashcardsReady={(d) => {
                      setFlashcardsDirect(d)
                      setTab("flashcards")
                    }}
                  />
                )}
                {tab === "quiz" && projectId && (
                  <QuizTaker
                    projectId={projectId}
                    focusConceptId={quizFocus}
                    onFocusConsumed={() => setQuizFocus(null)}
                    initialSession={quizDirect}
                    onSessionConsumed={() => setQuizDirect(null)}
                  />
                )}
                {tab === "practice" && projectId && (
                  <PracticePage
                    projectId={projectId}
                    onNavigate={goTab}
                    initialPlan={practiceDirect}
                    onPlanConsumed={() => setPracticeDirect(null)}
                  />
                )}
                {tab === "open-ended" && projectId && (
                  <OpenEndedAnswersPage projectId={projectId} onNavigate={goTab} />
                )}
                {tab === "flashcards" && projectId && (
                  <Flashcards
                    projectId={projectId}
                    initialDeck={flashcardsDirect}
                    onDeckConsumed={() => setFlashcardsDirect(null)}
                  />
                )}
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
                {tab === "analytics" && projectId && (
                  <AnalyticsPage
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
