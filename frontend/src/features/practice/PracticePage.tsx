import { useEffect, useMemo, useRef, useState } from "react"
import { motion } from "framer-motion"
import { Dumbbell, Loader2 } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Button, EmptyState, ErrorBox, LoadingState, PageHeader } from "@/components/ui"
import {
  KnowledgeTreeSelector,
  SelectionSummary,
  minimalCover,
  selectionCounts,
  type TreeTopic,
} from "@/components/knowledge/KnowledgeTreeSelector"
import { QuestionCountStepper } from "@/components/knowledge/QuestionCountStepper"
import { cn } from "@/lib/utils"
import { PracticeResults } from "./PracticeResults"
import { PracticeSession } from "./PracticeSession"
import type { ConceptMeta, McqItem, McqResult, OeItem, OeResult, PracticeLevel } from "./types"
import type { ProjectTab } from "@/features/dashboard/Dashboard"

type Stage = "select" | "configure" | "generating" | "session" | "results"

const LEVELS: { id: PracticeLevel; label: string; hint: string }[] = [
  { id: "adaptive", label: "Current level", hint: "Matched to mastery" },
  { id: "easy", label: "Easy", hint: "Foundations" },
  { id: "medium", label: "Medium", hint: "Understanding" },
  { id: "hard", label: "Hard", hint: "Deep mastery" },
]

const MAX_MCQS = 20
const MAX_OE = 10

export type PracticePlan = { conceptIds: string[]; mcqCount: number; oeCount: number }

export function PracticePage({
  projectId,
  onNavigate,
  initialPlan,
  onPlanConsumed,
}: {
  projectId: string
  onNavigate?: (tab: ProjectTab) => void
  initialPlan?: PracticePlan | null
  onPlanConsumed?: () => void
}) {
  const [topics, setTopics] = useState<TreeTopic[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [level, setLevel] = useState<PracticeLevel>("adaptive")
  const [mcqCount, setMcqCount] = useState(10)
  const [oeCount, setOeCount] = useState(3)
  const [stage, setStage] = useState<Stage>("select")
  const [genLabel, setGenLabel] = useState("Preparing your practice…")
  const [genError, setGenError] = useState<string | null>(null)

  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [mcq, setMcq] = useState<McqItem[]>([])
  const [oe, setOe] = useState<OeItem[]>([])
  const [results, setResults] = useState<{ mcq: McqResult[]; oe: OeResult[]; score: number | null } | null>(null)
  const planStarted = useRef(false)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ topics: TreeTopic[] }>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (!cancelled) setTopics(res.data.topics)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  const meta: ConceptMeta = useMemo(() => {    const m: ConceptMeta = new Map()
    for (const t of topics ?? []) {
      for (const s of t.subtopics) {
        for (const c of s.concepts) m.set(c.id, { topic: t.title, subtopic: s.title, concept: c.title })
      }
    }
    return m
  }, [topics])

  const counts = useMemo(() => selectionCounts(topics ?? [], checked), [topics, checked])

  const reset = () => {
    setStage("select")
    setGenError(null)
    setAttemptId(null)
    setMcq([])
    setOe([])
    setResults(null)
  }

  // Direct entry from the tutor plan flow: prefill + auto-start once knowledge loads.
  useEffect(() => {
    if (!initialPlan || !topics || planStarted.current) return
    planStarted.current = true
    setChecked(new Set(initialPlan.conceptIds))
    setMcqCount(Math.max(0, Math.min(20, initialPlan.mcqCount)))
    setOeCount(Math.max(0, Math.min(10, initialPlan.oeCount)))
    onPlanConsumed?.()
    // start() routes to session on success, or configure (prefilled) on error.
    void start({
      conceptIds: initialPlan.conceptIds,
      mcqCount: initialPlan.mcqCount,
      oeCount: initialPlan.oeCount,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPlan, topics])

  async function start(overrides?: { conceptIds?: string[]; mcqCount?: number; oeCount?: number }) {
    const effMcq = overrides?.mcqCount ?? mcqCount
    const effOe = overrides?.oeCount ?? oeCount
    const effCover = overrides?.conceptIds
      ? { topicIds: [] as string[], subtopicIds: [] as string[], conceptIds: overrides.conceptIds }
      : topics
        ? minimalCover(topics, checked)
        : null
    if (!effCover || (overrides == null && checked.size === 0)) return
    if (effMcq + effOe < 1) return
    setStage("generating")
    setGenError(null)
    try {
      let aid: string | null = null
      let questions: McqItem[] = []
      if (effMcq > 0) {
        setGenLabel(`Writing ${effMcq} multiple-choice questions…`)
        const gen = await apiClient.post<{ quiz_id: string }>(`/projects/${projectId}/quizzes/generate`, {
          scope: "practice",
          topic_ids: effCover.topicIds,
          subtopic_ids: effCover.subtopicIds,
          concept_ids: effCover.conceptIds,
          num_questions: effMcq,
          mode: "practice",
          difficulty: level === "adaptive" ? null : level,
        })
        setGenLabel("Starting your attempt…")
        const startRes = await apiClient.post<{ attempt_id: string; questions: McqItem[] }>(
          `/projects/${projectId}/quizzes/${gen.data.quiz_id}/attempts`,
        )
        aid = startRes.data.attempt_id
        questions = startRes.data.questions
      }
      const oeItems: OeItem[] = []
      for (let i = 0; i < effOe; i++) {
        setGenLabel(`Writing open-ended question ${i + 1} of ${effOe}…`)
        const res = await apiClient.post<OeItem>(`/projects/${projectId}/assessment/open-ended/generate`, {
          scope: "practice",
          topic_ids: effCover.topicIds,
          subtopic_ids: effCover.subtopicIds,
          concept_ids: effCover.conceptIds,
        })
        oeItems.push(res.data)
      }
      setAttemptId(aid)
      setMcq(questions)
      setOe(oeItems)
      setStage("session")
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setGenError(
        status === 429
          ? "Slow down — too many AI requests. Wait a moment and retry."
          : status === 502
            ? "AI provider unavailable — nothing was saved. Retry when ready."
            : status === 422
              ? (detail ?? "This selection has no practicable concepts yet — pick different knowledge.")
              : (detail ?? "Could not build your practice session."),
      )
      setStage("configure")
    }
  }

  return (
    <div className="min-h-full bg-slate-50">
      <div className="mx-auto max-w-5xl px-8 py-10">
        <PageHeader
          title="Practice"
          description="Practice what you've learned using questions grounded in your project knowledge."
        />

        {topics === null && !failed && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white px-6">
            <LoadingState text="Loading your knowledge…" />
          </div>
        )}
        {failed && (
          <div className="mt-6">
            <ErrorBox message="Could not load your knowledge tree." onRetry={() => window.location.reload()} />
          </div>
        )}
        {topics !== null && topics.length === 0 && stage === "select" && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white">
            <EmptyState
              icon={<Dumbbell size={24} />}
              title="Practice your knowledge"
              hint="Select topics, subtopics, or concepts and create a personalized practice session."
              action={
                <Button type="button" onClick={() => onNavigate?.("materials")}>
                  Upload material first
                </Button>
              }
            />
          </div>
        )}

        {topics !== null && topics.length > 0 && stage === "select" && (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
            <div className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6">
              <h2 className="mb-1 text-base font-semibold text-slate-900">What do you want to practice?</h2>
              <p className="mb-4 text-sm text-slate-500">Select any combination — an entire project, topics, subtopics, or individual concepts.</p>
              <KnowledgeTreeSelector topics={topics} checked={checked} onChange={setChecked} />
            </div>
            <div className="lg:sticky lg:top-6 lg:self-start">
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="text-sm font-semibold text-slate-900">Selection summary</h3>
                <div className="mt-2">
                  <SelectionSummary counts={counts} />
                </div>
                <p className="mt-1 text-xs text-slate-400">{counts.concepts} concepts selected</p>
                <Button type="button" disabled={counts.concepts === 0} onClick={() => setStage("configure")} className="mt-4 w-full">
                  Continue
                </Button>
                {counts.concepts === 0 && (
                  <p className="mt-2 text-center text-xs text-slate-400">Select at least one concept to continue.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {stage === "configure" && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto mt-6 max-w-2xl">
            <div className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
              <h2 className="text-base font-semibold text-slate-900">Configure your practice session</h2>
              <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/60 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-500">Selected knowledge</p>
                <p className="mt-1 text-sm font-medium text-slate-800">
                  {counts.topics} Topic{counts.topics === 1 ? "" : "s"} · {counts.subtopics} Subtopic{counts.subtopics === 1 ? "" : "s"} · {counts.concepts} Concept{counts.concepts === 1 ? "" : "s"}
                </p>
              </div>

              <div className="mt-5">
                <p className="mb-2 text-sm font-medium text-slate-700">Level</p>
                <div className="grid grid-cols-2 gap-2">
                  {LEVELS.map((l) => (
                    <button
                      key={l.id}
                      type="button"
                      onClick={() => setLevel(l.id)}
                      aria-pressed={level === l.id}
                      className={cn(
                        "rounded-lg border px-4 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                        level === l.id ? "border-indigo-500 bg-indigo-50" : "border-slate-200 hover:border-slate-300",
                      )}
                    >
                      <span className={cn("block text-sm font-medium", level === l.id ? "text-indigo-700" : "text-slate-600")}>{l.label}</span>
                      <span className="block text-xs text-slate-400">{l.hint}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <QuestionCountStepper label="How many MCQs?" hint="Multiple-choice questions" value={mcqCount} onChange={setMcqCount} min={0} max={MAX_MCQS} />
                <QuestionCountStepper label="How many Open-Ended Answers?" hint="Written answers, AI-evaluated" value={oeCount} onChange={setOeCount} min={0} max={MAX_OE} />
              </div>

              {genError && (
                <div className="mt-4">
                  <ErrorBox message={genError} onRetry={() => setGenError(null)} retryLabel="Dismiss" />
                </div>
              )}
              {mcqCount + oeCount < 1 && (
                <p className="mt-3 text-center text-xs text-amber-600">Request at least one question to start.</p>
              )}

              <div className="mt-6 flex gap-2">
                <Button type="button" variant="secondary" onClick={() => setStage("select")} className="flex-1">
                  Back
                </Button>
                <Button type="button" disabled={mcqCount + oeCount < 1} onClick={() => void start()} className="flex-[2]">
                  Start Practice
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {stage === "generating" && (
          <div className="mx-auto mt-6 max-w-2xl rounded-xl border border-slate-200 bg-white px-6 py-16 text-center">
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-indigo-600" />
            <p className="mt-3 text-sm font-medium text-slate-700" aria-live="polite">{genLabel}</p>
            <p className="mt-1 text-xs text-slate-400">Questions are written from your project knowledge.</p>
          </div>
        )}

        {stage === "session" && (
          <div className="mt-2">
            <PracticeSession
              projectId={projectId}
              attemptId={attemptId}
              mcq={mcq}
              oe={oe}
              meta={meta}
              onCancel={reset}
              onFinish={(r) => {
                setResults(r)
                setStage("results")
              }}
            />
          </div>
        )}

        {stage === "results" && results && (
          <div className="mt-2">
            <PracticeResults mcq={results.mcq} oe={results.oe} score={results.score} meta={meta} onRestart={reset} />
          </div>
        )}
      </div>
    </div>
  )
}
