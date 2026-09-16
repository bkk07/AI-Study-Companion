import { useEffect, useState } from "react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"

type Concept = { id: string; title: string; summary: string }
type Subtopic = { id: string; title: string; concepts: Concept[] }
type Topic = { id: string; title: string; subtopics: Subtopic[] }
type Structure = { topics: Topic[] }

export function StructureView({ projectId }: { projectId: string }) {
  const [structure, setStructure] = useState<Structure | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    apiClient
      .get<Structure>(`/projects/${projectId}/structure`)
      .then((res) => {
        if (!cancelled) setStructure(res.data)
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

  if (loading) {
    return <p className="mt-2 text-sm text-muted-foreground">Loading learning structure…</p>
  }

  if (error) {
    return (
      <div className="mt-2 rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">{error}</p>
        <button
          type="button"
          onClick={() => setReloadKey((k) => k + 1)}
          className="mt-2 text-sm text-primary hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!structure || structure.topics.length === 0) {
    return (
      <p className="mt-2 text-sm text-muted-foreground">
        No learning structure yet — upload a PDF and it will appear here once processed.
      </p>
    )
  }

  return (
    <ul className="mt-2 space-y-4">
      {structure.topics.map((topic) => (
        <li key={topic.id} className="rounded-md border p-4">
          <h3 className="font-semibold">{topic.title}</h3>
          {topic.subtopics.length === 0 ? (
            <p className="mt-1 text-sm text-muted-foreground">No subtopics yet.</p>
          ) : (
            <ul className="mt-2 space-y-3 pl-4">
              {topic.subtopics.map((sub) => (
                <li key={sub.id}>
                  <h4 className="text-sm font-medium">{sub.title}</h4>
                  {sub.concepts.length === 0 ? (
                    <p className="mt-1 text-sm text-muted-foreground">No concepts yet.</p>
                  ) : (
                    <ul className="mt-1 space-y-1 pl-4">
                      {sub.concepts.map((concept) => (
                        <li key={concept.id} className="text-sm">
                          <span className="font-medium">{concept.title}</span>
                          <span className="text-muted-foreground"> — {concept.summary}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  )
}
