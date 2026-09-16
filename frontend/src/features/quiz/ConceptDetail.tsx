import { useEffect, useState } from "react"
import { BookOpen, Play, X } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, Button, LoadingState, ProgressBar } from "@/components/ui"
import { cn } from "@/lib/utils"

export type RelatedHit = {
  id: string
  title: string
  lo_type: string
  importance: string
  topic: string
  subtopic: string
}

type Detail = {
  id: string
  title: string
  summary: string
  lo_type: string
  importance: string
  mastery: number | null
  status: string
  mcq: { value: number | null; count: number }
  applied: { value: number | null; count: number }
  questions_attempted: number
  questions_correct: number
  last_practiced_at: string | null
  prerequisites: RelatedHit[]
  related: RelatedHit[]
  supporting: RelatedHit[]
  source_material: string | null
  page_start: number | null
  page_end: number | null
}

export function statusTint(status: string): "muted" | "rose" | "amber" | "sky" | "emerald" {
  if (status === "Mastered") return "emerald"
  if (status === "Strong") return "sky"
  if (status === "Developing") return "amber"
  if (status === "Needs Practice") return "rose"
  return "muted"
}

function HitList({ label, hits, onOpen }: { label: string; hits: RelatedHit[]; onOpen: (id: string) => void }) {
  if (hits.length === 0) return null
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
      <ul className="mt-1.5 space-y-1">
        {hits.map((h) => (
          <li key={h.id}>
            <button
              type="button"
              onClick={() => onOpen(h.id)}
              className="text-sm font-medium text-violet-700 hover:underline"
            >
              {h.title}
            </button>
            <span className="ml-2 text-xs text-muted-foreground">
              {h.lo_type} · {h.topic} → {h.subtopic}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ConceptDetail({
  projectId,
  conceptId,
  onClose,
  onPractice,
  onOpen,
}: {
  projectId: string
  conceptId: string
  onClose: () => void
  onPractice: (conceptId: string) => void
  onOpen: (conceptId: string) => void
}) {
  const [detail, setDetail] = useState<Detail | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    setDetail(null)
    setFailed(false)
    apiClient
      .get<Detail>(`/projects/${projectId}/knowledge/concepts/${conceptId}`)
      .then((res) => {
        if (!cancelled) setDetail(res.data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId, conceptId])

  return (
    <div className="rounded-2xl border bg-card p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-violet-600">
          <BookOpen className="h-4 w-4" /> Learning target
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="rounded-lg p-1 text-muted-foreground hover:bg-muted"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {failed && <p className="mt-3 text-sm text-rose-600">Could not load details.</p>}
      {!failed && !detail && <LoadingState text="Loading details…" />}
      {detail && (
        <div className="mt-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-xl font-extrabold tracking-tight">{detail.title}</h3>
            <Badge tint="violet">{detail.lo_type}</Badge>
            <Badge tint={statusTint(detail.status)}>{detail.status}</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{detail.summary}</p>
          <div className="mt-4">
            <div className="flex items-baseline justify-between">
              <p className="text-sm font-bold">Mastery</p>
              <p className="text-sm font-extrabold text-gradient">
                {detail.mastery === null ? "Not started" : `${Math.round(detail.mastery)}%`}
              </p>
            </div>
            <ProgressBar value={detail.mastery} className="mt-1.5" />
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground sm:grid-cols-4">
              <span>Recognition: {detail.mcq.value === null ? "—" : `${Math.round(detail.mcq.value)}%`}</span>
              <span>Applied: {detail.applied.value === null ? "—" : `${Math.round(detail.applied.value)}%`}</span>
              <span>
                Questions: {detail.questions_correct}/{detail.questions_attempted} correct
              </span>
              <span>
                Last practiced:{" "}
                {detail.last_practiced_at
                  ? new Date(detail.last_practiced_at).toLocaleDateString()
                  : "never"}
              </span>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            <HitList label="Prerequisites" hits={detail.prerequisites} onOpen={onOpen} />
            <HitList label="Related" hits={detail.related} onOpen={onOpen} />
            <HitList label="Supporting knowledge" hits={detail.supporting} onOpen={onOpen} />
          </div>
          {(detail.source_material || detail.page_start !== null) && (
            <p className="mt-4 text-xs text-muted-foreground">
              Source: {detail.source_material ?? "material"}
              {detail.page_start !== null &&
                ` · pages ${detail.page_start}${
                  detail.page_end !== null && detail.page_end !== detail.page_start
                    ? `–${detail.page_end}`
                    : ""
                }`}
            </p>
          )}
          <Button type="button" onClick={() => onPractice(detail.id)} className={cn("mt-4")}>
            <Play className="h-4 w-4" /> Practice
          </Button>
        </div>
      )}
    </div>
  )
}
