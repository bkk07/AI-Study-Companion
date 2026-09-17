import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Button, ErrorBox, ProgressBar } from "@/components/ui"
import { GroundedChip } from "@/components/knowledge/EvaluationCard"
import { cn } from "@/lib/utils"
import { EVAL_STEPS, type ConceptMeta, type McqItem, type McqResult, type OeItem, type OeResult } from "./types"

const LETTERS = ["A", "B", "C", "D", "E", "F"]
const MIN_OE_CHARS = 20

function metaFor(meta: ConceptMeta, conceptId: string, fallback: string) {
  return meta.get(conceptId) ?? { topic: fallback, subtopic: "", concept: "" }
}

export function PracticeSession({
  projectId,
  attemptId,
  mcq,
  oe,
  meta,
  onFinish,
  onCancel,
}: {
  projectId: string
  attemptId: string | null
  mcq: McqItem[]
  oe: OeItem[]
  meta: ConceptMeta
  onFinish: (r: { mcq: McqResult[]; oe: OeResult[]; score: number | null }) => void
  onCancel: () => void
}) {
  const total = mcq.length + oe.length
  const [index, setIndex] = useState(0)
  const [mcqSel, setMcqSel] = useState<(number | null)[]>(() => mcq.map(() => null))
  const [oeText, setOeText] = useState<string[]>(() => oe.map(() => ""))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [evalState, setEvalState] = useState<{ current: number; total: number; step: number } | null>(null)
  const reduce = useReducedMotion()
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => () => {
    if (stepTimer.current) clearInterval(stepTimer.current)
  }, [])

  const isMcq = index < mcq.length
  const firstIncomplete = (): number | null => {
    for (let i = 0; i < mcq.length; i++) if (mcqSel[i] === null) return i
    for (let j = 0; j < oe.length; j++) if (oeText[j].trim().length < MIN_OE_CHARS) return mcq.length + j
    return null
  }

  async function submitAll() {
    const missing = firstIncomplete()
    if (missing !== null) {
      setIndex(missing)
      setError(
        missing < mcq.length
          ? "Answer every multiple-choice question before submitting."
          : `Each open-ended answer needs at least ${MIN_OE_CHARS} characters.`,
      )
      return
    }
    if (submitting) return
    setSubmitting(true)
    setError(null)
    try {
      // 1. Score MCQs server-side (no reveal — answers stay hidden until results).
      const mcqResults: McqResult[] = []
      if (attemptId) {
        for (let i = 0; i < mcq.length; i++) {
          const res = await apiClient.post<{ is_correct: boolean; correct_index: number }>(
            `/projects/${projectId}/quizzes/attempts/${attemptId}/answers`,
            { question_id: mcq[i].id, selected_index: mcqSel[i] },
          )
          mcqResults.push({ question: mcq[i], selected: mcqSel[i], isCorrect: res.data.is_correct, correctIndex: res.data.correct_index })
        }
      }
      let score: number | null = null
      if (attemptId) {
        const done = await apiClient.post<{ score: number | null }>(
          `/projects/${projectId}/quizzes/attempts/${attemptId}/complete`,
        )
        score = done.data.score
      } else if (mcqResults.length > 0) {
        score = Math.round((mcqResults.filter((m) => m.isCorrect).length / mcqResults.length) * 100)
      }

      // 2. Grade open-ended answers with a visible evaluation pipeline.
      const oeResults: OeResult[] = []
      for (let j = 0; j < oe.length; j++) {
        setEvalState({ current: j + 1, total: oe.length, step: 0 })
        stepTimer.current = setInterval(() => {
          setEvalState((s) => (s ? { ...s, step: Math.min(s.step + 1, EVAL_STEPS.length - 1) } : s))
        }, 850)
        try {
          const res = await apiClient.post(
            `/projects/${projectId}/assessment/open-ended`,
            { concept_id: oe[j].concept_id, answer_text: oeText[j].trim(), question_text: oe[j].question_text },
          )
          const g = res.data
          oeResults.push({
            question: oe[j],
            answer: oeText[j].trim(),
            grade: {
              score: g.score,
              verdict: g.verdict,
              feedback: g.feedback,
              strengths: g.strengths ?? [],
              missing_points: g.missing_points ?? [],
              suggestions: g.suggestions ?? [],
            },
            error: null,
          })
        } catch (e: unknown) {
          const { message: detail } = apiError(e)
          oeResults.push({ question: oe[j], answer: oeText[j].trim(), grade: null, error: detail ?? "Evaluation failed" })
        } finally {
          if (stepTimer.current) clearInterval(stepTimer.current)
          stepTimer.current = null
        }
      }
      setEvalState(null)
      onFinish({ mcq: mcqResults, oe: oeResults, score })
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setError(status === 429 ? "Slow down — too many AI requests. Wait a moment and retry." : (detail ?? "Submission failed — your answers are preserved."))
      setEvalState(null)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitting && evalState === null && oe.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-8 py-20 text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-indigo-600" />
        <p className="mt-3 text-sm text-slate-500">Submitting your practice…</p>
      </div>
    )
  }

  if (evalState) {
    return (
      <div className="mx-auto max-w-2xl px-8 py-16 text-center">
        <p className="text-sm font-semibold text-slate-800">
          Evaluating answer {evalState.current} of {evalState.total}
        </p>
        <div className="mx-auto mt-5 max-w-sm space-y-2.5 text-left">
          {EVAL_STEPS.map((s, i) => (
            <motion.p
              key={s}
              initial={reduce ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: i <= evalState.step ? 1 : 0.35, x: 0 }}
              className={cn("flex items-center gap-2 text-sm", i <= evalState.step ? "text-slate-700" : "text-slate-400")}
            >
              {i < evalState.step ? (
                <span className="text-green-500">✓</span>
              ) : i === evalState.step ? (
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
    )
  }

  const qMeta = isMcq
    ? metaFor(meta, mcq[index].concept_id, "Practice")
    : metaFor(meta, oe[index - mcq.length].concept_id, oe[index - mcq.length].scope_label)

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-900">
          Question {index + 1} <span className="font-normal text-slate-500">of {total}</span>
        </p>
        <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
          {isMcq ? "Multiple Choice" : "Open-Ended"}
        </span>
      </div>
      <ProgressBar value={(index / total) * 100} className="mt-2" barClass="bg-indigo-500" />

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span><strong className="font-medium text-slate-400">Topic:</strong> {qMeta.topic}</span>
        {qMeta.subtopic && <span><strong className="font-medium text-slate-400">Subtopic:</strong> {qMeta.subtopic}</span>}
        {qMeta.concept && <span><strong className="font-medium text-slate-400">Concept:</strong> {qMeta.concept}</span>}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={index}
          initial={reduce ? false : { opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={reduce ? undefined : { opacity: 0, x: -24 }}
          transition={{ duration: 0.18 }}
        >
          {isMcq ? (
            <div className="mt-4">
              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <p className="text-base font-semibold leading-snug text-slate-900">{mcq[index].question_text}</p>
              </div>
              <div className="mt-3 space-y-2" role="radiogroup" aria-label={`Options for question ${index + 1}`}>
                {mcq[index].options.map((opt, i) => (
                  <button
                    key={i}
                    type="button"
                    role="radio"
                    aria-checked={mcqSel[index] === i}
                    onClick={() => setMcqSel((prev) => prev.map((v, k) => (k === index ? i : v)))}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-medium transition-all",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                      mcqSel[index] === i
                        ? "border-indigo-400 bg-indigo-50"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
                    )}
                  >
                    <span className={cn(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
                      mcqSel[index] === i ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-500",
                    )}>
                      {LETTERS[i]}
                    </span>
                    <span className="text-slate-800">{opt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-xl border border-slate-200 bg-white p-6">
              <p className="text-base font-semibold leading-snug text-slate-900">{oe[index - mcq.length].question_text}</p>
              <textarea
                value={oeText[index - mcq.length]}
                onChange={(e) => setOeText((prev) => prev.map((v, k) => (k === index - mcq.length ? e.target.value : v)))}
                placeholder="Write your answer here..."
                rows={7}
                aria-label={`Answer for question ${index + 1}`}
                className="mt-4 w-full rounded-xl border border-slate-200 p-4 text-sm leading-relaxed text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-300 focus:ring-2 focus:ring-indigo-50"
              />
              <p className="mt-1 text-right text-xs text-slate-400" aria-live="polite">
                {oeText[index - mcq.length].trim().length} characters
                {oeText[index - mcq.length].trim().length < MIN_OE_CHARS ? ` · minimum ${MIN_OE_CHARS}` : ""}
              </p>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {error && (
        <div className="mt-4">
          <ErrorBox message={error} onRetry={() => setError(null)} retryLabel="Dismiss" />
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <div className="flex gap-2">
          <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
            Exit
          </Button>
          <Button type="button" variant="secondary" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0 || submitting}>
            <ArrowLeft size={14} /> Previous
          </Button>
        </div>
        {index + 1 < total ? (
          <Button type="button" onClick={() => setIndex((i) => Math.min(total - 1, i + 1))} disabled={submitting}>
            Next <ArrowRight size={14} />
          </Button>
        ) : (
          <Button type="button" onClick={() => void submitAll()} disabled={submitting}>
            {submitting ? "Submitting…" : "Submit Practice"}
          </Button>
        )}
      </div>
    </div>
  )
}
