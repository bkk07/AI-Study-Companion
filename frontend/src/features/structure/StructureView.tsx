import { useEffect, useState } from "react"
import { BookOpenText, ChevronDown, ListTree } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState } from "@/components/ui"
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

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    apiClient
      .get<Structure>(`/projects/${projectId}/structure`)
      .then((res) => {
        if (cancelled) return
        setStructure(res.data)
        // Expand the first topic by default.
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
      <EmptyState
        icon={<ListTree className="h-6 w-6" />}
        title="No learning map yet"
        hint="Upload a PDF and your Topic → Subtopic → Concept outline will appear here once processed."
      />
    )
  }

  return (
    <ul className="space-y-3">
      {structure.topics.map((topic, ti) => {
        const isOpen = open[topic.id] ?? false
        const conceptCount = topic.subtopics.reduce((n, s) => n + s.concepts.length, 0)
        return (
          <li key={topic.id} className="overflow-hidden rounded-2xl border bg-card shadow-soft">
            <button
              type="button"
              onClick={() => setOpen((o) => ({ ...o, [topic.id]: !isOpen }))}
              className="flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-violet-50/50"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-sm font-extrabold text-white">
                {ti + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-bold tracking-tight">{topic.title}</span>
                <span className="text-xs text-muted-foreground">
                  {topic.subtopics.length} subtopics · {conceptCount} concepts
                </span>
              </span>
              <ChevronDown className={cn("h-5 w-5 shrink-0 text-violet-500 transition-transform", isOpen && "rotate-180")} />
            </button>
            {isOpen && (
              <div className="animate-fade-up border-t bg-violet-50/40 px-4 py-3">
                {topic.subtopics.length === 0 ? (
                  <p className="py-2 text-sm text-muted-foreground">No subtopics yet.</p>
                ) : (
                  <ul className="space-y-3 py-1">
                    {topic.subtopics.map((sub) => (
                      <li key={sub.id} className="rounded-xl border bg-card p-3.5">
                        <p className="text-sm font-bold">{sub.title}</p>
                        {sub.concepts.length === 0 ? (
                          <p className="mt-1 text-sm text-muted-foreground">No concepts yet.</p>
                        ) : (
                          <ul className="mt-2 space-y-2">
                            {sub.concepts.map((concept) => (
                              <li key={concept.id} className="flex gap-2.5 text-sm">
                                <BookOpenText className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
                                <span>
                                  <span className="font-semibold">{concept.title}</span>
                                  <span className="text-muted-foreground"> — {concept.summary}</span>
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
