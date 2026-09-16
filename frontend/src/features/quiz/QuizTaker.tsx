import { useEffect, useState } from "react"
import { ArrowRight, CheckCircle2, PartyPopper, RotateCcw, Wand2, XCircle } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Badge, Button, EmptyState, ErrorBox, LoadingState, ProgressBar, Select } from "@/components/ui"
import { cn } from "@/lib/utils"

type Concept = { id: string; title: string }
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
  if (status === 422) return "Quiz generation failed validation — nothing was saved. Retry to generate again."
  if (status === 404) return "Quiz or project not found."
  return detail ?? "Request failed — nothing was lost except this click."
}

const LETTERS = ["A", "B", "C", "D", "E", "F"]

function difficultyTint(d: string): "violet" | "amber" | "rose" {
  if (d === "hard") return "rose"
  if (d === "medium") return "amber"
  return "violet"
}

export function QuizTaker({ projectId }: { projectId: string }) {
  const [concepts, setConcepts] = useState<Concept[] | null>(null)
  const [conceptId, setConceptId] = useState("")
  const [stage, setStage] = useState<Stage>({ name: "setup" })
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [confidence, setConfidence] = useState(3)
  const [reveal, setReveal] = useState<Reveal | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ topics: { subtopics: { concepts: Concept[] }[] }[] }>(`/projects/${projectId}/structure`)
      .then((res) => {
        if (cancelled) return
        const flat = res.data.topics.flatMap((t) => t.subtopics.flatMap((s) => s.concepts))
        setConcepts(flat)
        if (flat.length > 0) setConceptId(flat[0].id)
      })
      .catch(() => {
        if (!cancelled) setConcepts([])
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  async function generate() {
    if (!conceptId) return
    setStage({ name: "busy", label: "Generating quiz…" })
    const run = async () => {
      try {
        const gen = await apiClient.post<{ quiz_id: string }>(`/projects/${projectId}/quizzes/generate`, {
          concept_id: conceptId,
          num_questions: 5,
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
        { question_id: questions[index].id, selected_index: selected, confidence },
      )
      setReveal(res.data)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setSubmitError(errText(status, detail)) // attempt + selection preserved; retry re-submits
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

  if (concepts === null) return <LoadingState text="Loading concepts…" />

  if (stage.name === "setup" || stage.name === "busy") {
    return (
      <div>
        {concepts.length === 0 ? (
          <EmptyState
            icon={<Wand2 className="h-6 w-6" />}
            title="No concepts yet"
            hint="Upload a PDF and quizzes unlock once it's processed."
          />
        ) : (
          <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 p-5 text-white shadow-soft sm:p-6">
            <p className="flex items-center gap-2 font-bold">
              <Wand2 className="h-5 w-5" /> Generate an adaptive quiz
            </p>
            <p className="mt-1 text-sm text-white/80">
              Five questions tuned to the concept you pick — difficulty matched to your mastery.
            </p>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <Select
                value={conceptId}
                onChange={(e) => setConceptId(e.target.value)}
                disabled={stage.name === "busy"}
                className="flex-1 border-white/30 bg-white/15 text-white backdrop-blur [&>option]:text-foreground"
              >
                {concepts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </Select>
              <Button
                type="button"
                onClick={() => void generate()}
                disabled={stage.name === "busy" || !conceptId}
                className="bg-white text-violet-700 shadow-none hover:bg-white/90 hover:shadow-none"
              >
                {stage.name === "busy" ? "Working…" : "Generate quiz"}
              </Button>
            </div>
          </div>
        )}
        {stage.name === "busy" && (
          <p className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-300 border-t-violet-600" />
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
      <div className="flex flex-col items-center rounded-2xl border bg-gradient-to-b from-violet-50 to-card px-6 py-10 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white shadow-lift">
          <PartyPopper className="h-8 w-8" />
        </span>
        <p className="mt-4 text-5xl font-extrabold tracking-tight text-gradient">{pct}%</p>
        <p className="mt-1 font-bold">Quiz complete</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {stage.correct} of {stage.total} correct — mastery updated.
        </p>
        <Button
          type="button"
          variant="outline"
          className="mt-5"
          onClick={() => {
            setAttemptId(null)
            setQuestions([])
            setStage({ name: "setup" })
          }}
        >
          <RotateCcw className="h-4 w-4" /> Take another quiz
        </Button>
      </div>
    )
  }

  const q = questions[index]
  if (!q) return null
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-bold">
          Question {index + 1} <span className="font-medium text-muted-foreground">of {questions.length}</span>
        </p>
        <Badge tint={difficultyTint(q.difficulty)}>{q.difficulty}</Badge>
      </div>
      <ProgressBar value={questions.length ? (index / questions.length) * 100 : 0} className="mt-2" />
      <p className="mt-4 text-lg font-bold leading-snug tracking-tight">{q.question_text}</p>
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
                "flex w-full items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left text-sm font-medium transition-all",
                isCorrect
                  ? "border-emerald-400 bg-emerald-50 shadow-soft"
                  : isWrongPick
                    ? "border-rose-300 bg-rose-50"
                    : selected === i
                      ? "border-violet-500 bg-violet-50 shadow-glow"
                      : "border-border bg-card hover:border-violet-300 hover:bg-violet-50/50",
                reveal != null && "cursor-default",
              )}
            >
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-extrabold",
                  isCorrect
                    ? "bg-emerald-500 text-white"
                    : isWrongPick
                      ? "bg-rose-500 text-white"
                      : selected === i
                        ? "bg-violet-600 text-white"
                        : "bg-muted text-muted-foreground",
                )}
              >
                {isCorrect ? <CheckCircle2 className="h-4 w-4" /> : isWrongPick ? <XCircle className="h-4 w-4" /> : LETTERS[i]}
              </span>
              {opt}
            </button>
          )
        })}
      </div>
      {reveal == null ? (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Confidence</span>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setConfidence(n)}
                    disabled={submitting}
                    aria-label={`Confidence ${n}`}
                    className={cn(
                      "h-8 w-8 rounded-lg text-sm font-bold transition-all",
                      confidence >= n
                        ? "bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-soft"
                        : "bg-muted text-muted-foreground hover:bg-amber-100",
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <Button type="button" onClick={() => void submit()} disabled={selected == null || submitting} className="ml-auto">
              {submitting ? "Checking…" : <>Submit answer <ArrowRight className="h-4 w-4" /></>}
            </Button>
          </div>
          {submitError && (
            <div className="mt-3">
              <ErrorBox message={submitError} onRetry={() => void submit()} retryLabel="Retry submit" />
            </div>
          )}
        </>
      ) : (
        <div className={cn("mt-4 rounded-2xl border p-4", reveal.is_correct ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50")}>
          <p className={cn("flex items-center gap-1.5 font-bold", reveal.is_correct ? "text-emerald-700" : "text-amber-800")}>
            {reveal.is_correct ? <><CheckCircle2 className="h-5 w-5" /> Correct — nice!</> : "Not quite"}
          </p>
          {!reveal.is_correct && (
            <p className="mt-1 text-sm">
              Correct answer: <strong>{q.options[reveal.correct_index]}</strong>
            </p>
          )}
          <p className="mt-1 text-xs text-muted-foreground">
            Running score: {reveal.correct_count}/{reveal.answered_count}
          </p>
          <Button type="button" onClick={() => void next()} className="mt-3">
            {index + 1 < questions.length ? <>Next question <ArrowRight className="h-4 w-4" /></> : "Finish quiz"}
          </Button>
        </div>
      )}
    </div>
  )
}
