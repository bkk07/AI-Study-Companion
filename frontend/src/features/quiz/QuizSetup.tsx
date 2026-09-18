import { useEffect, useMemo, useState } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { Loader2, Search, Sparkles } from "lucide-react"
import apiClient from "@/lib/axios"
import { estimateMinutes } from "@/lib/estimate"
import { EmptyState, SectionHeader } from "@/components/ui"
import {
  AnimatedNumber,
  KnowledgeTreeSelector,
  minimalCover,
  selectionCounts,
  TreeSkeleton,
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
  status?: string
}

type Recommendations = { items: Candidate[]; fallback: Candidate | null }

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
  const [treeRetryKey, setTreeRetryKey] = useState(0)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [recs, setRecs] = useState<Recommendations | null>(null)
  const [focusId, setFocusId] = useState<string | null>(null)
  const reduce = useReducedMotion()

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
    setTreeFailed(false)
    setTopics(null)
    apiClient
      .get<{ topics: TreeTopic[] }>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (!cancelled) setTopics(res.data.topics)
      })
      .catch(() => {
        if (!cancelled) setTreeFailed(true)
      })
    apiClient
      .get<Recommendations>(`/projects/${projectId}/practice/recommendations?limit=4`)
      .then((res) => {
        if (!cancelled) setRecs(res.data)
      })
      .catch(() => {
        if (!cancelled) setRecs({ items: [], fallback: null })
      })
    return () => {
      cancelled = true
    }
  }, [projectId, treeRetryKey])

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

  const quizThis = (conceptId: string) =>
    onStart({
      scope: "practice",
      topicIds: [],
      subtopicIds: [],
      conceptIds: [conceptId],
      selectedConceptCount: 1,
      numQuestions: qCount,
    })

  const hero = recs?.items[0] ?? recs?.fallback ?? null
  const heroIsFresh = hero != null && typeof hero.mastery !== "number"
  const hasEvidence = (recs?.items ?? []).some((c) => typeof c.mastery === "number")

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 pb-28 sm:px-6 lg:pb-8">
      <SectionHeader
        title="Adaptive Quiz"
        subtitle={
          recs == null
            ? "Questions are selected based on your mastery evidence."
            : hasEvidence
              ? "Questions are selected weakest-first, matched to your mastery."
              : "No quiz history yet — starting with foundational concepts in curriculum order."
        }
      />

      {hero && (
        <div className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-indigo-100 bg-white px-5 py-4 shadow-sm">
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-indigo-500">
              <Sparkles size={12} /> {heroIsFresh ? "Suggested starting point" : "Recommended for you"}
            </p>
            <p className="mt-0.5 truncate text-base font-semibold text-slate-900">{hero.name}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {typeof hero.mastery === "number" ? (
                <>
                  Mastery{" "}
                  <strong className="font-mono-data text-slate-700">{Math.round(hero.mastery)}%</strong>
                  {hero.status ? <> · {hero.status}</> : null}
                </>
              ) : (
                <>{hero.reasoning} Questions start easy and build up.</>
              )}
            </p>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={() => quizThis(hero.concept_id)}
            className="shrink-0 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            Quiz this →
          </button>
        </div>
      )}

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="grid grid-cols-1 items-start gap-6 lg:grid-cols-5"
      >
        <section
          aria-label="Knowledge selection"
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 lg:col-span-3"
        >
          <h3 className="text-base font-semibold text-slate-900">What do you want to practice?</h3>
          <p className="mt-1 text-sm text-slate-500">
            Select topics, subtopics, or individual concepts from your knowledge base.
          </p>
          <div className="mt-4">
            {topics === null && !treeFailed && <TreeSkeleton rows={3} />}
            {treeFailed && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                <p className="text-xs text-red-600">
                  Could not load your knowledge tree — check your connection, then try again.
                </p>
                <button
                  type="button"
                  onClick={() => setTreeRetryKey((k) => k + 1)}
                  className="mt-2 rounded-lg bg-white px-3.5 py-1.5 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-200 hover:bg-red-100"
                >
                  Try again
                </button>
              </div>
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
        </section>

        <aside aria-label="Quiz settings" className="lg:col-span-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 lg:sticky lg:top-6">
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

            <div className="mt-5 border-t border-slate-100 pt-4" aria-live="polite">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Quiz summary</p>
              <dl className="mt-2 space-y-1.5 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Concepts</dt>
                  <dd className="font-mono-data font-semibold text-slate-900">
                    <AnimatedNumber value={counts.concepts} />
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Questions</dt>
                  <dd className="font-mono-data font-semibold text-slate-900">{qCount}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Estimated time</dt>
                  <dd className="font-medium text-slate-900">{estimateMinutes({ mcq: qCount })}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Difficulty</dt>
                  <dd className="font-medium text-slate-900">Adaptive</dd>
                </div>
              </dl>
            </div>

            <button
              type="button"
              onClick={start}
              disabled={!valid || busy}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy && <Loader2 size={17} className="animate-spin" />}
              {busy ? "Preparing your quiz..." : "Start Quiz →"}
            </button>
            {!valid && (
              <p className="mt-2 text-center text-xs text-slate-400">Select at least one concept to start.</p>
            )}
          </div>
        </aside>
      </motion.div>

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
