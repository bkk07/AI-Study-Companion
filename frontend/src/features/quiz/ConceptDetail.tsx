import { useEffect, useState } from "react"
import { BookOpen, Play, X } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, Button, LoadingState, ProgressBar, Tag } from "@/components/ui"
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
  final_mastery?: number | null
  evidence_confidence?: string
  streams?: Record<string, { value: number | null; count: number }>
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
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <ul className="mt-1.5 space-y-1">
        {hits.map((h) => (
          <li key={h.id}>
            <button
              type="button"
              onClick={() => onOpen(h.id)}
              className="text-sm font-medium text-indigo-600 hover:underline"
            >
              {h.title}
            </button>
            <span className="ml-2 text-xs text-slate-400">
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
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <BookOpen size={14} /> Learning target
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
        >
          <X size={16} />
        </button>
      </div>
      {failed && <p className="mt-3 text-sm text-red-600">Could not load details.</p>}
      {!failed && !detail && <LoadingState text="Loading details…" />}
      {detail && (
        <div className="mt-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold text-slate-900">{detail.title}</h3>
            <Tag color="indigo">{detail.lo_type}</Tag>
            <Badge tint={statusTint(detail.status)}>{detail.status}</Badge>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">{detail.summary}</p>
          <div className="mt-4">
            <div className="flex items-baseline justify-between">
              <p className="text-sm font-semibold text-slate-800">Mastery</p>
              <p className="font-mono-data text-sm font-semibold text-slate-800">
                {detail.mastery === null ? "Not started" : `${Math.round(detail.mastery)}%`}
              </p>
            </div>
            <ProgressBar value={detail.mastery} className="mt-1.5" barClass="bg-indigo-500" />
            {detail.final_mastery !== null && detail.final_mastery !== undefined && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <span className="font-semibold text-slate-700">
                  Final: <span className="font-mono-data">{Math.round(detail.final_mastery)}%</span>
                </span>
                {detail.evidence_confidence === "low" && (
                  <span
                    title="Fewer than 3 evidence rows — treat this mastery as an early estimate"
                    className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
                  >
                    Early estimate
                  </span>
                )}
              </div>
            )}
            {detail.streams && Object.keys(detail.streams).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(
                  [
                    ["quiz", "Quiz"],
                    ["open_ended", "Open-ended"],
                    ["practice", "Practice"],
                    ["flashcard", "Flashcards"],
                    ["tutor", "Tutor"],
                  ] as const
                ).map(([key, label]) => {
                  const s = detail.streams?.[key]
                  return (
                    <span
                      key={key}
                      title={`${label}: ${s && s.value !== null ? `${Math.round(s.value)}% over ${s.count} evidence` : "no evidence yet"}`}
                      className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600"
                    >
                      {label} {s && s.value !== null ? `${Math.round(s.value)}%` : "—"}
                    </span>
                  )
                })}
              </div>
            )}
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-4">
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
            <p className="mt-4 text-xs text-slate-400">
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
            <Play size={14} /> Practice
          </Button>
        </div>
      )}
    </div>
  )
}
