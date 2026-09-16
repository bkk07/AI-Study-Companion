import { useEffect, useState } from "react"
import { BookOpenText, ChevronDown, ChevronRight, ListTree } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, MasteryDot, SectionHeader, masteryLevelFor } from "@/components/ui"
import { cn } from "@/lib/utils"

type Concept = { id: string; title: string; summary: string }
type Subtopic = { id: string; title: string; concepts: Concept[] }
type Topic = { id: string; title: string; subtopics: Subtopic[] }
type Structure = { topics: Topic[] }

export function StructureView({ projectId }: { projectId: string }) {
  const [structure, setStructure] = useState<Structure | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const [selected, setSelected] = useState<Concept | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    apiClient
      .get<Structure>(`/projects/${projectId}/structure`)
      .then((res) => {
        if (cancelled) return
        setStructure(res.data)
        const first = res.data.topics[0]
        if (first) setOpen({ [first.id]: true })
      })
      .catch((e: unknown) => {
        if (cancelled) return
        const { status, message: detail } = apiError(e)
        if (status === 404) setError("Learning structure not found for this project.")
        else setError(detail ?? "Failed to load learning structure")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectId, reloadKey])

  if (loading) return <LoadingState text="Loading learning structure…" />
  if (error) return <ErrorBox message={error} onRetry={() => setReloadKey((k) => k + 1)} />
  if (!structure || structure.topics.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white">
        <EmptyState
          icon={<ListTree size={24} />}
          title="No learning map yet"
          hint="Upload a PDF and your Topic → Subtopic → Concept outline will appear here once processed."
        />
      </div>
    )
  }

  const totalConcepts = structure.topics.reduce(
    (n, t) => n + t.subtopics.reduce((m, s) => m + s.concepts.length, 0),
    0,
  )

  return (
    <div className={cn(selected && "mr-0 lg:mr-96")}>
      <SectionHeader
        title="Knowledge Map"
        subtitle={`${structure.topics.length} topics · ${totalConcepts} concepts grounded in your PDFs`}
      />
      <div className="max-w-3xl space-y-3">
        {structure.topics.map((topic) => {
          const isOpen = open[topic.id] ?? false
          const conceptCount = topic.subtopics.reduce((n, s) => n + s.concepts.length, 0)
          return (
            <div key={topic.id} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <button
                type="button"
                onClick={() => setOpen((o) => ({ ...o, [topic.id]: !isOpen }))}
                className="flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-slate-50"
              >
                <ChevronDown size={16} className={cn("shrink-0 text-slate-400 transition-transform", isOpen && "rotate-180")} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-slate-900">{topic.title}</span>
                  <span className="text-xs text-slate-400">
                    {topic.subtopics.length} subtopics · {conceptCount} concepts
                  </span>
                </span>
                <span className="font-mono-data text-xs text-slate-500">{conceptCount} concepts</span>
              </button>
              {isOpen && (
                <div className="border-t border-slate-100 px-4 py-3">
                  {topic.subtopics.length === 0 ? (
                    <p className="py-2 text-sm text-slate-500">No subtopics yet.</p>
                  ) : (
                    <div className="space-y-4 py-1">
                      {topic.subtopics.map((sub) => (
                        <div key={sub.id} className="ml-6">
                          <p className="text-sm font-semibold text-slate-800">{sub.title}</p>
                          <p className="text-xs text-slate-400">{sub.concepts.length} concepts</p>
                          {sub.concepts.length === 0 ? (
                            <p className="mt-1 text-sm text-slate-500">No concepts yet.</p>
                          ) : (
                            <div className="mt-2 space-y-1">
                              {sub.concepts.map((concept) => (
                                <button
                                  key={concept.id}
                                  type="button"
                                  onClick={() => setSelected(concept)}
                                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-slate-50"
                                >
                                  <MasteryDot level={masteryLevelFor(null)} />
                                  <span className="min-w-0 flex-1 truncate text-sm text-slate-700">{concept.title}</span>
                                  <ChevronRight size={14} className="shrink-0 text-slate-300" />
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {selected && (
        <div className="fixed bottom-0 right-0 top-14 z-30 w-full max-w-md overflow-y-auto border-l border-slate-200 bg-white p-6 shadow-xl lg:w-96">
          <div className="flex items-start justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-400">Concept</div>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100"
            >
              Close
            </button>
          </div>
          <h3 className="mt-2 flex items-start gap-2 text-lg font-semibold text-slate-900">
            <BookOpenText size={18} className="mt-1 shrink-0 text-indigo-500" />
            {selected.title}
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{selected.summary || "No summary yet."}</p>
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-relaxed text-slate-500">
            Grounded in your uploaded PDFs. Ask the Tutor for a cited explanation or start a Quiz on this concept.
          </div>
        </div>
      )}
    </div>
  )
}
