import { useState } from "react"
import { ArrowRight, CheckCircle2, Info, PartyPopper, RotateCcw, XCircle } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Badge, Button, ErrorBox, ProgressBar } from "@/components/ui"
import { cn } from "@/lib/utils"
import { QuizSetup, type QuizStartPayload } from "./QuizSetup"

type Question = { id: string; question_text: string; options: string[]; difficulty: string; concept_id: string }
type Reveal = { is_correct: boolean; correct_index: number; answered_count: number; correct_count: number }
type Stage =
  | { name: "setup" }
  | { name: "busy"; label: string }
  | { name: "answering" }
  | { name: "done"; score: number | null; correct: number; total: number }
  | { name: "failure"; text: string; retry: () => void }

function errText(status?: number, detail?: string): string {
  if (status === 429) return "Slow down — too many AI requests. Wait a moment and retry."
  if (status === 502) return "Quiz AI provider unavailable — nothing was saved. Retry when ready."
  if (status === 422) return detail ?? "This target can't be quizzed (supporting material has no practice mode) — pick a CORE target."
  if (status === 404) return "Quiz or project not found."
  return detail ?? "Request failed — nothing was lost except this click."
}

const LETTERS = ["A", "B", "C", "D", "E", "F"]

function difficultyTint(d: string): "violet" | "amber" | "rose" {
  if (d === "hard") return "rose"
  if (d === "medium") return "amber"
  return "violet"
}

export function QuizTaker({
  projectId,
  focusConceptId,
  onFocusConsumed,
}: {
  projectId: string
  focusConceptId?: string | null
  onFocusConsumed?: () => void
}) {
  const [stage, setStage] = useState<Stage>({ name: "setup" })
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [confidence, setConfidence] = useState<"low" | "medium" | "high">("medium")
  const [confidenceValue, setConfidenceValue] = useState(3)
  const [reveal, setReveal] = useState<Reveal | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  async function generate(payload: QuizStartPayload) {
    setStage({ name: "busy", label: "Generating quiz…" })
    const run = async () => {
      try {
        const gen = await apiClient.post<{ quiz_id: string }>(`/projects/${projectId}/quizzes/generate`, {
          scope: payload.scope,
          topic_id: payload.topicId ?? null,
          subtopic_id: payload.subtopicId ?? null,
          concept_id: payload.conceptId ?? null,
          num_questions: payload.numQuestions,
          mode: "practice",
        })
        setStage({ name: "busy", label: "Starting attempt…" })
        const start = await apiClient.post<{ attempt_id: string; questions: Question[] }>(
          `/projects/${projectId}/quizzes/${gen.data.quiz_id}/attempts`,
        )
        setAttemptId(start.data.attempt_id)
        setQuestions(start.data.questions)
        setIndex(0)
        setSelected(null)
        setReveal(null)
        setStage({ name: "answering" })
      } catch (e: unknown) {
        const { status, message: detail } = apiError(e)
        setStage({ name: "failure", text: errText(status, detail), retry: () => void run() })
      }
    }
    await run()
  }

  async function submit() {
    if (attemptId == null || selected == null || submitting) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await apiClient.post<Reveal>(
        `/projects/${projectId}/quizzes/attempts/${attemptId}/answers`,
        { question_id: questions[index].id, selected_index: selected, confidence: confidenceValue },
      )
      setReveal(res.data)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setSubmitError(errText(status, detail))
    } finally {
      setSubmitting(false)
    }
  }

  async function next() {
    if (attemptId == null) return
    if (index + 1 < questions.length) {
      setIndex(index + 1)
      setSelected(null)
      setReveal(null)
      return
    }
    setStage({ name: "busy", label: "Completing attempt…" })
    try {
      const res = await apiClient.post<{ score: number | null; correct_count: number; total: number }>(
        `/projects/${projectId}/quizzes/attempts/${attemptId}/complete`,
      )
      setStage({ name: "done", score: res.data.score, correct: res.data.correct_count, total: res.data.total })
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setStage({ name: "failure", text: errText(status, detail), retry: () => void next() })
    }
  }

  if (stage.name === "setup" || stage.name === "busy") {
    return (
      <div>
        <QuizSetup
          projectId={projectId}
          busy={stage.name === "busy"}
          onStart={(p) => void generate(p)}
          initialConceptId={focusConceptId}
          onConsumed={onFocusConsumed}
        />
        {stage.name === "busy" && (
          <p className="mx-auto mt-3 flex max-w-2xl items-center gap-2 px-8 text-sm text-slate-500">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
            {stage.label}
          </p>
        )}
      </div>
    )
  }

  if (stage.name === "failure") {
    return <ErrorBox message={stage.text} onRetry={stage.retry} retryLabel="Retry" />
  }

  if (stage.name === "done") {
    const pct = stage.score ?? 0
    return (
      <div className="mx-auto max-w-4xl rounded-xl border border-slate-200 bg-white p-8 text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
          <PartyPopper size={22} />
        </span>
        <p className={cn("font-mono-data mt-4 text-5xl font-bold", pct >= 70 ? "text-green-600" : pct >= 40 ? "text-amber-600" : "text-red-600")}>{pct}%</p>
        <p className="mt-1 text-base font-semibold text-slate-900">Quiz complete</p>
        <p className="mt-1 text-sm text-slate-500">
          {stage.correct} of {stage.total} correct — mastery updated.
        </p>
        <Button
          type="button"
          variant="secondary"
          className="mt-5"
          onClick={() => {
            setAttemptId(null)
            setQuestions([])
            setStage({ name: "setup" })
          }}
        >
          <RotateCcw size={14} /> Take another quiz
        </Button>
      </div>
    )
  }

  const q = questions[index]
  if (!q) return null
  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-900">
          Question {index + 1} <span className="font-normal text-slate-500">of {questions.length}</span>
        </p>
        <Badge tint={difficultyTint(q.difficulty)}>{q.difficulty}</Badge>
      </div>
      <ProgressBar value={questions.length ? (index / questions.length) * 100 : 0} className="mt-2" barClass="bg-indigo-500" />
      <div className="mt-4 flex gap-2 rounded-xl border border-indigo-100 bg-indigo-50 p-4">
        <Info size={15} className="mt-0.5 shrink-0 text-indigo-600" />
        <p className="text-xs leading-relaxed text-slate-600">
          <span className="font-semibold text-slate-800">Why this question? </span>
          Tuned to your weakest concept based on recognition vs. applied mastery.
        </p>
      </div>
      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-7">
        <p className="text-base font-semibold leading-snug text-slate-900">{q.question_text}</p>
      </div>
      <div className="mt-4 space-y-2">
        {q.options.map((opt, i) => {
          const isCorrect = reveal && i === reveal.correct_index
          const isWrongPick = reveal && selected === i && !reveal.is_correct
          return (
            <button
              key={i}
              type="button"
              disabled={reveal != null || submitting}
              onClick={() => setSelected(i)}
              className={cn(
                "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-medium transition-all",
                isCorrect
                  ? "border-green-300 bg-green-50"
                  : isWrongPick
                    ? "border-red-200 bg-red-50"
                    : selected === i
                      ? "border-indigo-300 bg-indigo-50"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
                reveal != null && "cursor-default",
              )}
            >
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
                  isCorrect
                    ? "bg-green-500 text-white"
                    : isWrongPick
                      ? "bg-red-500 text-white"
                      : selected === i
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-500",
                )}
              >
                {isCorrect ? <CheckCircle2 size={14} /> : isWrongPick ? <XCircle size={14} /> : LETTERS[i]}
              </span>
              <span className="text-slate-800">{opt}</span>
            </button>
          )
        })}
      </div>
      {reveal == null ? (
        <>
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Confidence</p>
            <div className="mt-2 flex gap-2">
              {(["low", "medium", "high"] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => {
                    setConfidence(c)
                    setConfidenceValue(c === "low" ? 1 : c === "medium" ? 3 : 5)
                  }}
                  disabled={submitting}
                  className={cn(
                    "flex-1 rounded-lg border px-3 py-2 text-sm font-medium capitalize transition-colors",
                    confidence === c
                      ? c === "low"
                        ? "border-red-200 bg-red-50 text-red-700"
                        : c === "medium"
                          ? "border-amber-200 bg-amber-50 text-amber-700"
                          : "border-green-200 bg-green-50 text-green-700"
                      : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50",
                  )}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <Button type="button" onClick={() => void submit()} disabled={selected == null || submitting}>
              {submitting ? "Checking…" : <>Submit answer <ArrowRight size={14} /></>}
            </Button>
          </div>
          {submitError && (
            <div className="mt-3">
              <ErrorBox message={submitError} onRetry={() => void submit()} retryLabel="Retry submit" />
            </div>
          )}
        </>
      ) : (
        <div className={cn("mt-4 rounded-xl border p-4", reveal.is_correct ? "border-green-200 bg-green-50" : "border-amber-200 bg-amber-50")}>
          <p className={cn("flex items-center gap-1.5 text-sm font-semibold", reveal.is_correct ? "text-green-700" : "text-amber-800")}>
            {reveal.is_correct ? <><CheckCircle2 size={16} /> Correct — nice!</> : "Not quite"}
          </p>
          {!reveal.is_correct && (
            <p className="mt-1 text-sm text-slate-700">
              Correct answer: <strong>{q.options[reveal.correct_index]}</strong>
            </p>
          )}
          <p className="mt-1 text-xs text-slate-500">
            Running score: {reveal.correct_count}/{reveal.answered_count}
          </p>
          <Button type="button" onClick={() => void next()} className="mt-3">
            {index + 1 < questions.length ? <>Next question <ArrowRight size={14} /></> : "Finish quiz"}
          </Button>
        </div>
      )}
    </div>
  )
}
