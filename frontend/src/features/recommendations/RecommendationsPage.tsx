import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Compass } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { ErrorBox, LoadingState, SectionHeader } from "@/components/ui"

type Space = { id: string; name: string }
type Project = { id: string; name: string; space_id: string }
type Recommendation = {
  id: string
  concept_id: string
  concept_name: string
  action_type: string
  score: number
  reasoning: string
  status: string
  topic: string
  subtopic: string
  concept_path: string
}
type Dashboard = { recommendation: Recommendation | null }
type Entry = { space: Space; project: Project; recommendation: Recommendation | null }

const ACTION_TABS: Record<string, string> = {
  ask_tutor: "tutor",
  targeted_quiz: "quiz",
  explain_back: "open-ended",
  review_material: "materials",
  exam_mode: "quiz",
}

function projectLink(spaceId: string, projectId: string, tab: string): string {
  return `/spaces/${spaceId}/projects/${projectId}?tab=${tab}`
}

export function RecommendationsPage() {
  const [entries, setEntries] = useState<Entry[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const spacesRes = await apiClient.get<Space[]>("/spaces")
      const spaces = spacesRes.data
      const projectLists = await Promise.all(
        spaces.map((s) => apiClient.get<Project[]>(`/spaces/${s.id}/projects`)),
      )
      const pairs = spaces.flatMap((space, i) =>
        projectLists[i].data.map((project) => ({ space, project })),
      )
      const dashboards = await Promise.all(
        pairs.map(({ project }) =>
          apiClient
            .get<Dashboard>(`/projects/${project.id}/dashboard`)
            .then((r) => r.data.recommendation)
            .catch(() => null),
        ),
      )
      setEntries(
        pairs.map(({ space, project }, i) => ({
          space,
          project,
          recommendation: dashboards[i],
        })),
      )
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to load recommendations.")
      setEntries(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return (
      <div className="bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <LoadingState text="Loading recommendations…" />
        </div>
      </div>
    )
  }

  if (error || entries === null) {
    return (
      <div className="bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <ErrorBox message={error ?? "Failed to load recommendations."} onRetry={() => void load()} />
        </div>
      </div>
    )
  }

  const withRec = entries.filter((e) => e.recommendation !== null)

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-5xl px-8 py-10">
        <SectionHeader
          title="Recommendations"
          subtitle="The current next action for every project — quiz completions recompute these automatically."
        />
        {entries.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-8 py-14 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <Compass size={24} />
            </div>
            <h3 className="text-lg font-semibold text-slate-800">No projects yet</h3>
            <p className="mx-auto mt-1 max-w-xs text-sm text-slate-500">
              Create a space and project, upload material, and complete a quiz to get your first
              recommendation.
            </p>
            <Link
              to="/spaces"
              className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Go to spaces <ArrowRight size={15} />
            </Link>
          </div>
        ) : withRec.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-8 py-14 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <Compass size={24} />
            </div>
            <h3 className="text-lg font-semibold text-slate-800">Nothing scorable yet</h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
              Recommendations appear once a project has concepts and learning evidence — upload
              material and complete a quiz or practice round first.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {entries.map(({ space, project, recommendation }) =>
              recommendation ? (
                <li
                  key={project.id}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white"
                >
                  <Link
                    to={projectLink(
                      space.id,
                      project.id,
                      ACTION_TABS[recommendation.action_type] ?? "overview",
                    )}
                    className="group flex items-center gap-4 px-6 py-4 transition-colors hover:bg-indigo-50/40"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-xs font-bold text-indigo-700">
                      {recommendation.concept_name.trim()[0]?.toUpperCase() ?? "•"}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-slate-800">
                        {recommendation.action_type.replace(/_/g, " ")}
                        {recommendation.concept_name ? ` · ${recommendation.concept_name}` : ""}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {project.name} ({space.name}) — {recommendation.reasoning}
                      </span>
                    </span>
                    <ArrowRight
                      size={15}
                      className="shrink-0 text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-500"
                    />
                  </Link>
                </li>
              ) : (
                <li
                  key={project.id}
                  className="flex items-center gap-4 rounded-xl border border-dashed border-slate-200 bg-white/60 px-6 py-4"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-500">
                      {project.name}
                      <span className="ml-2 text-xs text-slate-400">({space.name})</span>
                    </span>
                    <span className="block truncate text-xs text-slate-400">
                      No recommendation yet — complete a quiz or practice round first.
                    </span>
                  </span>
                  <Link
                    to={projectLink(space.id, project.id, "overview")}
                    className="shrink-0 text-sm font-medium text-indigo-600 hover:underline"
                  >
                    Open
                  </Link>
                </li>
              ),
            )}
          </ul>
        )}
      </div>
    </div>
  )
}
