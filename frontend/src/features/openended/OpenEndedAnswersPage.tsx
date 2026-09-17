import { useEffect, useMemo, useRef, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { ArrowLeft, ArrowRight, Loader2, PenLine, RotateCcw } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Button, EmptyState, ErrorBox, LoadingState, PageHeader, ProgressBar } from "@/components/ui"
import {
  KnowledgeTreeSelector,
  SelectionSummary,
  minimalCover,
  selectionCounts,
  type TreeTopic,
} from "@/components/knowledge/KnowledgeTreeSelector"
import { QuestionCountStepper } from "@/components/knowledge/QuestionCountStepper"
import { EvaluationCard, GroundedChip, type OEGrade } from "@/components/knowledge/EvaluationCard"
import { cn } from "@/lib/utils"
import type { ConceptMeta } from "@/features/practice/types"
import { EVAL_STEPS } from "@/features/practice/types"
import type { ProjectTab } from "@/features/dashboard/Dashboard"

type Stage = "setup" | "generating" | "answering" | "evaluating" | "results"

type GenQuestion = {
  question_text: string
  concept_id: string
  scope_label: string
  difficulty: string | null
}

type AnswerState = {
  question: GenQuestion
  answer: string
  grade: OEGrade | null
  error: string | null
  grading: boolean
}

const MAX_QUESTIONS = 10
const MIN_CHARS = 20

function errText(status?: number, detail?: string): string {
  if (status === 429) return "Slow down — too many AI requests. Wait a moment and retry."
  if (status === 502) return "AI provider unavailable — nothing was saved. Retry when ready."
  if (status === 422) return detail ?? "This selection has no practicable concepts yet — pick different knowledge."
  if (status === 404) return "Project or knowledge not found."
  return detail ?? "Request failed — nothing was saved."
}

export function OpenEndedAnswersPage({
  projectId,
  onNavigate,
}: {
  projectId: string
  onNavigate?: (tab: ProjectTab) => void
}) {
  const [topics, setTopics] = useState<TreeTopic[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [count, setCount] = useState(5)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [stage, setStage] = useState<Stage>("setup")
  const [error, setError] = useState<string | null>(null)
  const [genProgress, setGenProgress] = useState({ current: 0, total: 0 })
  const [answers, setAnswers] = useState<AnswerState[]>([])
  const [index, setIndex] = useState(0)
  const [evalStep, setEvalStep] = useState(0)
  const reduce = useReducedMotion()
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null)

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

  useEffect(() => () => {
    if (stepTimer.current) clearInterval(stepTimer.current)
  }, [])

  const meta: ConceptMeta = useMemo(() => {
    const m: ConceptMeta = new Map()
    for (const t of topics ?? []) {
      for (const s of t.subtopics) {
        for (const c of s.concepts) m.set(c.id, { topic: t.title, subtopic: s.title, concept: c.title })
      }
    }
    return m
  }, [topics])

  const counts = useMemo(() => selectionCounts(topics ?? [], checked), [topics, checked])
  const metaFor = (conceptId: string, fallback: string) =>
    meta.get(conceptId) ?? { topic: fallback, subtopic: "", concept: "" }

  const reset = () => {
    setStage("setup")
    setError(null)
    setAnswers([])
    setIndex(0)
  }

  async function generate() {
    if (!topics || counts.concepts === 0) return
    const cover = minimalCover(topics, checked)
    setStage("generating")
    setError(null)
    setGenProgress({ current: 0, total: count })
    try {
      const items: AnswerState[] = []
      for (let i = 0; i < count; i++) {
        setGenProgress({ current: i + 1, total: count })
        const res = await apiClient.post<GenQuestion>(`/projects/${projectId}/assessment/open-ended/generate`, {
          scope: "practice",
          topic_ids: cover.topicIds,
          subtopic_ids: cover.subtopicIds,
          concept_ids: cover.conceptIds,
        })
        items.push({ question: res.data, answer: "", grade: null, error: null, grading: false })
      }
      setAnswers(items)
      setIndex(0)
      setStage("answering")
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setError(errText(status, detail))
      setStage("setup")
    }
  }

  async function gradeOne(i: number): Promise<boolean> {
    const item = answers[i]
    if (!item || item.answer.trim().length < MIN_CHARS) return false
    setAnswers((prev) => prev.map((a, k) => (k === i ? { ...a, grading: true, error: null } : a)))
    setEvalStep(0)
    stepTimer.current = setInterval(() => setEvalStep((s) => Math.min(s + 1, EVAL_STEPS.length - 1)), 850)
    try {
      const res = await apiClient.post(`/projects/${projectId}/assessment/open-ended`, {
        concept_id: item.question.concept_id,
        answer_text: item.answer.trim(),
        question_text: item.question.question_text,
      })
      const g = res.data
      const grade: OEGrade = {
        score: g.score,
        verdict: g.verdict,
        feedback: g.feedback,
        strengths: g.strengths ?? [],
        missing_points: g.missing_points ?? [],
        suggestions: g.suggestions ?? [],
      }
      setAnswers((prev) => prev.map((a, k) => (k === i ? { ...a, grade, grading: false } : a)))
      return true
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setAnswers((prev) =>
        prev.map((a, k) => (k === i ? { ...a, grading: false, error: errText(status, detail) } : a)),
      )
      return false
    } finally {
      if (stepTimer.current) clearInterval(stepTimer.current)
      stepTimer.current = null
    }
  }

  async function submitAll() {
    const firstShort = answers.findIndex((a) => a.answer.trim().length < MIN_CHARS)
    if (firstShort !== -1) {
      setIndex(firstShort)
      setError(`Each answer needs at least ${MIN_CHARS} characters before submitting.`)
      return
    }
    setError(null)
    setStage("evaluating")
    for (let i = 0; i < answers.length; i++) {
      setIndex(i)
      await gradeOne(i)
    }
    setStage("results")
  }

  const graded = answers.filter((a) => a.grade !== null)
  const avgScore = graded.length > 0 ? graded.reduce((s, a) => s + (a.grade?.score ?? 0), 0) / graded.length : null
  const byTopic = new Map<string, number[]>()
  for (const a of graded) {
    const t = metaFor(a.question.concept_id, a.question.scope_label).topic
    if (!byTopic.has(t)) byTopic.set(t, [])
    byTopic.get(t)?.push(a.grade?.score ?? 0)
  }

  return (
    <div className="min-h-full bg-slate-50">
      <div className="mx-auto max-w-5xl px-8 py-10">
        <PageHeader
          title="Open Ended Answers"
          description="Explain concepts in your own words and evaluate your understanding using your project knowledge."
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
        {topics !== null && topics.length === 0 && stage === "setup" && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white">
            <EmptyState
              icon={<PenLine size={24} />}
              title="Test your understanding"
              hint="Generate open-ended questions from the knowledge you've studied."
              action={
                <Button type="button" onClick={() => onNavigate?.("materials")}>
                  Upload material first
                </Button>
              }
            />
          </div>
        )}

        {topics !== null && topics.length > 0 && stage === "setup" && (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
            <div className="space-y-6">
              <div className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6">
                <h2 className="mb-4 text-base font-semibold text-slate-900">How many questions do you want to generate?</h2>
                <QuestionCountStepper label="Number of questions" hint={`1 to ${MAX_QUESTIONS} open-ended questions`} value={count} onChange={setCount} min={1} max={MAX_QUESTIONS} />
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6">
                <h2 className="mb-1 text-base font-semibold text-slate-900">What should these questions cover?</h2>
                <p className="mb-4 text-sm text-slate-500">Select an entire project, topics, subtopics, or individual concepts.</p>
                <KnowledgeTreeSelector topics={topics} checked={checked} onChange={setChecked} />
              </div>
            </div>
            <div className="lg:sticky lg:top-6 lg:self-start">
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="text-sm font-semibold text-slate-900">Session summary</h3>
                <p className="mt-1 text-sm text-slate-600">{count} question{count === 1 ? "" : "s"}</p>
                <div className="mt-2">
                  <SelectionSummary counts={counts} />
                </div>
                {error && (
                  <div className="mt-3">
                    <ErrorBox message={error} onRetry={() => setError(null)} retryLabel="Dismiss" />
                  </div>
                )}
                <Button type="button" disabled={counts.concepts === 0} onClick={() => void generate()} className="mt-4 w-full">
                  Create Questions
                </Button>
                {counts.concepts === 0 && (
                  <p className="mt-2 text-center text-xs text-slate-400">Select at least one concept to continue.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {stage === "generating" && (
          <div className="mx-auto mt-6 max-w-2xl rounded-xl border border-slate-200 bg-white px-6 py-16 text-center">
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-indigo-600" />
            <p className="mt-3 text-sm font-medium text-slate-700" aria-live="polite">
              Generating questions… {genProgress.current} of {genProgress.total}
            </p>
            <p className="mt-1 text-xs text-slate-400">Each question is written from your project knowledge.</p>
          </div>
        )}

        {stage === "answering" && answers.length > 0 && (
          <div className="mx-auto mt-6 max-w-3xl">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-900">
                Question {index + 1} <span className="font-normal text-slate-500">of {answers.length}</span>
              </p>
              <GroundedChip />
            </div>
            <ProgressBar value={(index / answers.length) * 100} className="mt-2" barClass="bg-indigo-500" />

            {(() => {
              const item = answers[index]
              const m = metaFor(item.question.concept_id, item.question.scope_label)
              return (
                <div>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span><strong className="font-medium text-slate-400">Topic:</strong> {m.topic}</span>
                    {m.subtopic && <span><strong className="font-medium text-slate-400">Subtopic:</strong> {m.subtopic}</span>}
                    {m.concept && <span><strong className="font-medium text-slate-400">Concept:</strong> {m.concept}</span>}
                  </div>
                  <AnimatePresence mode="wait" initial={false}>
                    <motion.div
                      key={index}
                      initial={reduce ? false : { opacity: 0, x: 24 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={reduce ? undefined : { opacity: 0, x: -24 }}
                      transition={{ duration: 0.18 }}
                      className="mt-4 rounded-xl border border-slate-200 bg-white p-6"
                    >
                      <p className="text-base font-semibold leading-snug text-slate-900">{item.question.question_text}</p>
                      <textarea
                        value={item.answer}
                        onChange={(e) => setAnswers((prev) => prev.map((a, k) => (k === index ? { ...a, answer: e.target.value } : a)))}
                        placeholder="Write your answer..."
                        rows={7}
                        aria-label={`Answer for question ${index + 1}`}
                        className="mt-4 w-full rounded-xl border border-slate-200 p-4 text-sm leading-relaxed text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-300 focus:ring-2 focus:ring-indigo-50"
                      />
                      <p className="mt-1 text-right text-xs text-slate-400" aria-live="polite">
                        {item.answer.trim().length} characters
                        {item.answer.trim().length < MIN_CHARS ? ` · minimum ${MIN_CHARS}` : ""}
                      </p>
                    </motion.div>
                  </AnimatePresence>
                </div>
              )
            })()}

            {error && (
              <div className="mt-4">
                <ErrorBox message={error} onRetry={() => setError(null)} retryLabel="Dismiss" />
              </div>
            )}

            <div className="mt-6 flex items-center justify-between">
              <div className="flex gap-2">
                <Button type="button" variant="secondary" onClick={reset}>
                  Exit
                </Button>
                <Button type="button" variant="secondary" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
                  <ArrowLeft size={14} /> Previous
                </Button>
              </div>
              {index + 1 < answers.length ? (
                <Button type="button" onClick={() => setIndex((i) => Math.min(answers.length - 1, i + 1))}>
                  Next <ArrowRight size={14} />
                </Button>
              ) : (
                <Button type="button" onClick={() => void submitAll()}>
                  Submit Answers
                </Button>
              )}
            </div>
          </div>
        )}

        {stage === "evaluating" && (
          <div className="mx-auto mt-6 max-w-2xl rounded-xl border border-slate-200 bg-white px-6 py-14 text-center">
            <p className="text-sm font-semibold text-slate-800" aria-live="polite">
              Evaluating answer {Math.min(index + 1, answers.length)} of {answers.length}
            </p>
            <div className="mx-auto mt-5 max-w-sm space-y-2.5 text-left">
              {EVAL_STEPS.map((s, i) => (
                <motion.p
                  key={s}
                  initial={reduce ? false : { opacity: 0, x: -8 }}
                  animate={{ opacity: i <= evalStep ? 1 : 0.35, x: 0 }}
                  className={cn("flex items-center gap-2 text-sm", i <= evalStep ? "text-slate-700" : "text-slate-400")}
                >
                  {i < evalStep ? (
                    <span className="text-green-500">✓</span>
                  ) : i === evalStep ? (
                    <Loader2 size={14} className="animate-spin text-indigo-600" />
                  ) : (
                    <span className="text-slate-300">·</span>
                  )}
                  {s}
                </motion.p>
              ))}
            </div>
            <div className="mt-4 flex justify-center"><GroundedChip /></div>
          </div>
        )}

        {stage === "results" && (
          <div className="mx-auto mt-6 max-w-3xl space-y-6">
            <div className="rounded-xl bg-indigo-600 p-6 text-white sm:p-8">
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-200">Open-Ended Practice Complete</p>
              <div className="mt-3 flex flex-wrap gap-6">
                <div>
                  <p className="font-mono-data text-3xl font-bold">{answers.length}</p>
                  <p className="text-sm text-indigo-200">Questions</p>
                </div>
                <div>
                  <p className="font-mono-data text-3xl font-bold">{graded.length}</p>
                  <p className="text-sm text-indigo-200">Evaluated{avgScore !== null ? ` · avg ${Math.round(avgScore)}` : ""}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={reset}
                className="mt-5 inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
              >
                <RotateCcw size={14} /> Create new questions
              </button>
            </div>

            {byTopic.size > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <h3 className="mb-4 text-sm font-semibold text-slate-900">Understanding by Topic</h3>
                <div className="space-y-3">
                  {[...byTopic.entries()].map(([t, scores]) => {
                    const v = scores.reduce((a, b) => a + b, 0) / scores.length
                    return (
                      <div key={t}>
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="truncate text-sm text-slate-700">{t}</span>
                          <span className="font-mono-data text-sm font-semibold text-slate-800">{Math.round(v)}%</span>
                        </div>
                        <ProgressBar value={v} className="mt-1" barClass={v >= 80 ? "bg-green-500" : v >= 50 ? "bg-amber-500" : "bg-red-500"} />
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {answers.map((a, i) => {
              const m = metaFor(a.question.concept_id, a.question.scope_label)
              return a.grade ? (
                <EvaluationCard key={i} index={`· ${i + 1}`} question={a.question.question_text} answer={a.answer} grade={a.grade} knowledge={m} />
              ) : (
                <div key={i} className="rounded-xl border border-slate-200 bg-white p-5">
                  <p className="text-sm font-medium text-slate-800">Question {i + 1}: {a.question.question_text}</p>
                  <p className="mt-2 whitespace-pre-line rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">{a.answer}</p>
                  <div className="mt-3">
                    <ErrorBox
                      message={a.error ?? "Evaluation failed."}
                      onRetry={() => void gradeOne(i)}
                      retryLabel="Retry evaluation"
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
