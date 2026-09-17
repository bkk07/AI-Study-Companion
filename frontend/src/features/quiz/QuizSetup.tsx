import { useEffect, useMemo, useRef, useState } from "react"
import { Loader2, Search, Sparkles } from "lucide-react"
import apiClient from "@/lib/axios"
import { EmptyState, LoadingState, SectionHeader } from "@/components/ui"
import {
  KnowledgeTreeSelector,
  minimalCover,
  selectionCounts,
  type TreeTopic,
} from "@/components/knowledge/KnowledgeTreeSelector"
import { QuestionCountStepper } from "@/components/knowledge/QuestionCountStepper"
import { cn } from "@/lib/utils"

export type QuizStartPayload = {
  scope: "practice"
  topicIds: string[]
  subtopicIds: string[]
  conceptIds: string[]
  selectedConceptCount: number
  numQuestions: number
}

type Candidate = {
  concept_id: string
  name: string
  reasoning: string
  mastery?: number | null
}

type Recommendations = { items: Candidate[]; fallback: Candidate | null }

function estimateMinutes(n: number): string {
  const mins = Math.max(1, Math.round(n * 1.5))
  return `~${mins} minute${mins === 1 ? "" : "s"}`
}

export function QuizSetup({
  projectId,
  busy,
  onStart,
  initialConceptId,
  onConsumed,
}: {
  projectId: string
  busy: boolean
  onStart: (payload: QuizStartPayload) => void
  initialConceptId?: string | null
  onConsumed?: () => void
}) {
  const [qCount, setQCount] = useState(10)
  const [topics, setTopics] = useState<TreeTopic[] | null>(null)
  const [treeFailed, setTreeFailed] = useState(false)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [recs, setRecs] = useState<Recommendations | null>(null)
  const [focusId, setFocusId] = useState<string | null>(null)
  const settingsRef = useRef<HTMLDivElement>(null)

  // Deep link from Dashboard ("Study this"): preselect the concept in the tree.
  useEffect(() => {
    if (initialConceptId) {
      setChecked(new Set([initialConceptId]))
      setFocusId(initialConceptId)
      onConsumed?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialConceptId])

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ topics: TreeTopic[] }>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (!cancelled) setTopics(res.data.topics)
      })
      .catch(() => {
        if (!cancelled) setTreeFailed(true)
      })
    apiClient
      .get<Recommendations>(`/projects/${projectId}/practice/recommendations?limit=3`)
      .then((res) => {
        if (!cancelled) setRecs(res.data)
      })
      .catch(() => {
        if (!cancelled) setRecs({ items: [], fallback: null })
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  const counts = useMemo(() => selectionCounts(topics ?? [], checked), [topics, checked])
  const valid = counts.concepts > 0

  const start = () => {
    if (!valid || busy || !topics) return
    const cover = minimalCover(topics, checked)
    onStart({
      scope: "practice",
      topicIds: cover.topicIds,
      subtopicIds: cover.subtopicIds,
      conceptIds: cover.conceptIds,
      selectedConceptCount: counts.concepts,
      numQuestions: qCount,
    })
  }

  const hero = recs?.items[0] ?? recs?.fallback ?? null

  return (
    <div className="mx-auto max-w-2xl px-8 py-10 pb-28 lg:pb-10">
      <SectionHeader title="Adaptive Quiz" subtitle="Questions are selected based on your mastery evidence." />

      {hero && (
        <div className="mb-5 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-white p-5 shadow-sm">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-500">
            <Sparkles size={12} /> Recommended
          </p>
          <p className="text-base font-semibold text-slate-900">{hero.name}</p>
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">
            Take a targeted quiz based on your mastery evidence. {hero.reasoning}
          </p>
          {typeof hero.mastery === "number" && (
            <p className="mt-2 text-xs text-slate-500">
              Mastery <strong className="font-mono-data text-slate-800">{Math.round(hero.mastery)}%</strong>
            </p>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              onStart({
                scope: "practice",
                topicIds: [],
                subtopicIds: [],
                conceptIds: [hero.concept_id],
                selectedConceptCount: 1,
                numQuestions: qCount,
              })
            }
            className="mt-3 inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            Quiz me →
          </button>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h3 className="text-base font-semibold text-slate-900">Quiz configuration</h3>
        <p className="mt-1 text-sm font-medium text-slate-700">What do you want to practice?</p>

        <div className="mt-4">
          {topics === null && !treeFailed && <LoadingState text="Loading your knowledge…" />}
          {treeFailed && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              Could not load topics — upload material first, then come back.
            </p>
          )}
          {topics !== null && topics.length === 0 && (
            <EmptyState
              icon={<Search size={20} />}
              title="No topics yet"
              hint="Upload a PDF and adaptive quizzes unlock once it's processed."
            />
          )}
          {topics !== null && topics.length > 0 && (
            <KnowledgeTreeSelector
              topics={topics}
              checked={checked}
              onChange={setChecked}
              expandConceptId={focusId}
            />
          )}
        </div>

        <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3" aria-live="polite">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Selected knowledge</p>
          <p className="mt-1 text-sm font-medium text-slate-800">
            {counts.concepts} concept{counts.concepts === 1 ? "" : "s"} · {counts.subtopics} subtopic{counts.subtopics === 1 ? "" : "s"} · {counts.topics} topic{counts.topics === 1 ? "" : "s"}
          </p>
        </div>

        <div className="mt-3 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setChecked(new Set())}
            className="text-xs font-medium text-slate-400 transition-colors hover:text-red-600 hover:underline"
          >
            Clear selection
          </button>
          <button
            type="button"
            onClick={() => settingsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
            className="text-sm font-semibold text-indigo-600 hover:underline"
          >
            Continue →
          </button>
        </div>
      </div>

      <div ref={settingsRef} className="mt-6 scroll-mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h3 className="text-base font-semibold text-slate-900">Quiz settings</h3>

        <div className="mt-4">
          <QuestionCountStepper
            label="Number of questions"
            hint="5 to 20 adaptive questions"
            value={qCount}
            onChange={setQCount}
            min={5}
            max={20}
            step={5}
          />
        </div>

        <div className="mt-4">
          <p className="mb-1 text-sm font-semibold text-slate-800">Difficulty</p>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm font-medium text-indigo-700">
            Adaptive
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
            Questions are chosen based on mastery evidence and detected mismatches.
          </p>
        </div>

        <p className="mt-4 text-xs text-slate-400">
          Estimated time <strong className="font-medium text-slate-600">{estimateMinutes(qCount)}</strong>
        </p>
      </div>

      <div className="mt-6 hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:block sm:p-8">
        <h3 className="text-base font-semibold text-slate-900">Ready to practice?</h3>
        <ul className="mt-2 space-y-1 text-sm text-slate-600">
          <li>{counts.concepts} concept{counts.concepts === 1 ? "" : "s"} selected</li>
          <li>{qCount} questions</li>
          <li>Adaptive difficulty</li>
          <li>{estimateMinutes(qCount)}</li>
        </ul>
        {!valid && (
          <p className="mt-3 text-sm text-slate-500">
            Select what you want to practice — choose a project, topic, subtopic, or individual concepts from your knowledge base.
          </p>
        )}
        <button
          type="button"
          onClick={start}
          disabled={!valid || busy}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy && <Loader2 size={17} className="animate-spin" />}
          {busy ? "Preparing your quiz..." : "Start Quiz"}
        </button>
      </div>

      {/* Mobile sticky action bar */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center gap-3">
          <span className="min-w-0 flex-1 truncate text-sm text-slate-600" aria-live="polite">
            <strong className={cn("font-semibold", valid ? "text-slate-900" : "text-slate-400")}>
              {counts.concepts} concept{counts.concepts === 1 ? "" : "s"}
            </strong>{" "}
            selected
          </span>
          <button
            type="button"
            onClick={start}
            disabled={!valid || busy}
            className="flex shrink-0 items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            {busy ? "Preparing..." : "Start Quiz"}
          </button>
        </div>
        {!valid && (
          <p className="mt-1 truncate text-center text-[11px] text-slate-400">
            Select topics, subtopics, or concepts above to begin.
          </p>
        )}
      </div>
    </div>
  )
}
