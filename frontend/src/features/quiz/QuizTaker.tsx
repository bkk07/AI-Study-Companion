import { useEffect, useState } from "react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"

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
  if (status === 502) return "Quiz AI provider unavailable — nothing was saved. Retry when ready."
  if (status === 422) return "Quiz generation failed validation — nothing was saved. Retry to generate again."
  if (status === 404) return "Quiz or project not found."
  return detail ?? "Request failed — nothing was lost except this click."
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

  if (concepts === null) return <p className="mt-2 text-sm text-muted-foreground">Loading concepts…</p>

  if (stage.name === "setup" || stage.name === "busy") {
    return (
      <div className="mt-2">
        {concepts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No concepts yet — upload a PDF and quizzes unlock once processed.</p>
        ) : (
          <div className="flex gap-2">
            <select
              value={conceptId}
              onChange={(e) => setConceptId(e.target.value)}
              disabled={stage.name === "busy"}
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm disabled:opacity-50"
            >
              {concepts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void generate()}
              disabled={stage.name === "busy" || !conceptId}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Generate quiz
            </button>
          </div>
        )}
        {stage.name === "busy" && <p className="mt-2 text-sm text-muted-foreground">{stage.label}</p>}
      </div>
    )
  }

  if (stage.name === "failure") {
    return (
      <div className="mt-2 rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">{stage.text}</p>
        <button type="button" onClick={stage.retry} className="mt-2 text-sm text-primary hover:underline">
          Retry
        </button>
      </div>
    )
  }

  if (stage.name === "done") {
    return (
      <div className="mt-2 rounded-md border p-4">
        <p className="font-semibold">Quiz complete</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Score: {stage.score ?? 0}% ({stage.correct}/{stage.total} correct)
        </p>
        <button
          type="button"
          onClick={() => {
            setAttemptId(null)
            setQuestions([])
            setStage({ name: "setup" })
          }}
          className="mt-2 text-sm text-primary hover:underline"
        >
          Take another quiz
        </button>
      </div>
    )
  }

  const q = questions[index]
  if (!q) return null
  return (
    <div className="mt-2 rounded-md border p-4">
      <p className="text-xs text-muted-foreground">
        Question {index + 1} of {questions.length} · {q.difficulty}
      </p>
      <p className="mt-1 text-sm font-medium">{q.question_text}</p>
      <div className="mt-2 space-y-1">
        {q.options.map((opt, i) => (
          <label
            key={i}
            className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
              reveal && i === reveal.correct_index ? "border-green-500 bg-green-500/10" : ""
            } ${reveal && selected === i && !reveal.is_correct ? "border-destructive bg-destructive/10" : ""}`}
          >
            <input
              type="radio"
              name="option"
              checked={selected === i}
              disabled={reveal != null || submitting}
              onChange={() => setSelected(i)}
            />
            {opt}
          </label>
        ))}
      </div>
      {reveal == null ? (
        <>
        <div className="mt-3 flex items-center gap-3">
          <label className="text-xs text-muted-foreground">
            Confidence
            <select
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              disabled={submitting}
              className="ml-2 rounded-md border bg-background px-2 py-1 text-sm"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={selected == null || submitting}
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit answer"}
          </button>
        </div>
        {submitError && (
          <div className="mt-2 rounded-md border border-destructive/50 bg-destructive/10 p-2 text-sm">
            <p className="text-destructive">{submitError}</p>
            <button type="button" onClick={() => void submit()} className="mt-1 text-sm text-primary hover:underline">
              Retry submit
            </button>
          </div>
        )}
        </>
      ) : (
        <div className="mt-3">
          <p className={`text-sm font-medium ${reveal.is_correct ? "text-green-600" : "text-destructive"}`}>
            {reveal.is_correct ? "Correct" : `Incorrect — correct answer: ${q.options[reveal.correct_index]}`}
          </p>
          <p className="text-xs text-muted-foreground">
            Running score: {reveal.correct_count}/{reveal.answered_count}
          </p>
          <button type="button" onClick={() => void next()} className="mt-2 text-sm text-primary hover:underline">
            {index + 1 < questions.length ? "Next question" : "Finish quiz"}
          </button>
        </div>
      )}
    </div>
  )
}
