import { motion, useReducedMotion } from "framer-motion"
import { CheckCircle2, RotateCcw, XCircle } from "lucide-react"
import { ProgressBar } from "@/components/ui"
import { EvaluationCard } from "@/components/knowledge/EvaluationCard"
import { cn } from "@/lib/utils"
import type { ConceptMeta, McqResult, OeResult } from "./types"

function avg(xs: number[]): number | null {
  if (xs.length === 0) return null
  return xs.reduce((a, b) => a + b, 0) / xs.length
}

function Bar({ label, value, sub }: { label: string; value: number; sub: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-sm text-slate-700">{label}</span>
        <span className="shrink-0 text-xs text-slate-500">
          <strong className={cn("font-mono-data text-sm", value >= 80 ? "text-green-600" : value >= 50 ? "text-amber-600" : "text-red-600")}>
            {Math.round(value)}%
          </strong>{" "}
          · {sub}
        </span>
      </div>
      <ProgressBar value={value} className="mt-1" barClass={value >= 80 ? "bg-green-500" : value >= 50 ? "bg-amber-500" : "bg-red-500"} />
    </div>
  )
}

export function PracticeResults({
  mcq,
  oe,
  score,
  meta,
  onRestart,
}: {
  mcq: McqResult[]
  oe: OeResult[]
  score: number | null
  meta: ConceptMeta
  onRestart: () => void
}) {
  const reduce = useReducedMotion()
  const correct = mcq.filter((m) => m.isCorrect).length
  const graded = oe.filter((o) => o.grade !== null)
  const oeAvg = avg(graded.map((o) => o.grade?.score ?? 0))

  const byTopic = new Map<string, number[]>()
  const bySub = new Map<string, { topic: string; scores: number[] }>()
  const byConcept = new Map<string, { path: string; scores: number[] }>()
  const push = (conceptId: string, v: number) => {
    const m = meta.get(conceptId) ?? { topic: "Other", subtopic: "Other", concept: "Concept" }
    if (!byTopic.has(m.topic)) byTopic.set(m.topic, [])
    byTopic.get(m.topic)?.push(v)
    const sk = `${m.topic} › ${m.subtopic}`
    if (!bySub.has(sk)) bySub.set(sk, { topic: m.topic, scores: [] })
    bySub.get(sk)?.scores.push(v)
    if (!byConcept.has(m.concept)) byConcept.set(m.concept, { path: `${m.topic} › ${m.subtopic}`, scores: [] })
    byConcept.get(m.concept)?.scores.push(v)
  }
  for (const m of mcq) push(m.question.concept_id, m.isCorrect ? 100 : 0)
  for (const o of graded) push(o.question.concept_id, o.grade?.score ?? 0)

  const topics = [...byTopic.entries()].map(([t, s]) => ({ label: t, value: avg(s) ?? 0, n: s.length }))
  const subs = [...bySub.entries()].map(([s, v]) => ({ label: s, value: avg(v.scores) ?? 0, n: v.scores.length }))
  const concepts = [...byConcept.entries()].map(([c, v]) => ({ label: c, path: v.path, value: avg(v.scores) ?? 0, n: v.scores.length }))

  return (
    <motion.div initial={reduce ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-3xl space-y-6 px-8 py-10">
      <div className="rounded-xl bg-indigo-600 p-6 text-white sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-200">Practice Complete</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <div>
            <p className="font-mono-data text-3xl font-bold">
              {correct}<span className="text-lg text-indigo-200">/{mcq.length}</span>
            </p>
            <p className="text-sm text-indigo-200">MCQs · {mcq.length - correct} incorrect</p>
          </div>
          <div>
            <p className="font-mono-data text-3xl font-bold">
              {graded.length}<span className="text-lg text-indigo-200">/{oe.length}</span>
            </p>
            <p className="text-sm text-indigo-200">Open-ended evaluated{oeAvg !== null ? ` · avg ${Math.round(oeAvg)}` : ""}</p>
          </div>
          <div>
            <p className="font-mono-data text-3xl font-bold">{score ?? "—"}{score !== null && <span className="text-lg text-indigo-200">%</span>}</p>
            <p className="text-sm text-indigo-200">Overall practice summary</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onRestart}
          className="mt-5 inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
        >
          <RotateCcw size={14} /> Start new practice
        </button>
      </div>

      {topics.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Performance by Topic</h3>
          <div className="space-y-3">
            {topics.map((t) => (
              <Bar key={t.label} label={t.label} value={t.value} sub={`${t.n} answer${t.n === 1 ? "" : "s"}`} />
            ))}
          </div>
        </div>
      )}

      {subs.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Performance by Subtopic</h3>
          <div className="space-y-3">
            {subs.map((s) => (
              <Bar key={s.label} label={s.label} value={s.value} sub={`${s.n} answer${s.n === 1 ? "" : "s"}`} />
            ))}
          </div>
        </div>
      )}

      {concepts.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Performance by Concept</h3>
          <div className="space-y-3">
            {concepts.map((c) => (
              <div key={c.label}>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-slate-700">{c.label}</span>
                    <span className="block truncate text-[11px] text-slate-400">{c.path}</span>
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">
                    <strong className={cn("font-mono-data text-sm", c.value >= 80 ? "text-green-600" : c.value >= 50 ? "text-amber-600" : "text-red-600")}>
                      {Math.round(c.value)}%
                    </strong>
                  </span>
                </div>
                <ProgressBar value={c.value} className="mt-1" barClass={c.value >= 80 ? "bg-green-500" : c.value >= 50 ? "bg-amber-500" : "bg-red-500"} />
              </div>
            ))}
          </div>
        </div>
      )}

      {mcq.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-3 text-sm font-semibold text-slate-900">MCQ Review</h3>
          <ul className="space-y-2">
            {mcq.map((m, i) => (
              <li key={m.question.id} className="rounded-lg border border-slate-100 px-3 py-2.5 text-sm">
                <p className="flex items-start gap-2 font-medium text-slate-800">
                  {m.isCorrect ? <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-green-500" /> : <XCircle size={15} className="mt-0.5 shrink-0 text-red-500" />}
                  <span><span className="text-slate-400">Q{i + 1} · </span>{m.question.question_text}</span>
                </p>
                <p className="ml-6 mt-1 text-xs text-slate-500">
                  Your answer: <strong className={m.isCorrect ? "text-green-700" : "text-red-600"}>{m.selected !== null ? m.question.options[m.selected] : "—"}</strong>
                  {!m.isCorrect && (
                    <> · Correct: <strong className="text-green-700">{m.question.options[m.correctIndex]}</strong></>
                  )}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {oe.map((o, i) => {
        const m = meta.get(o.question.concept_id) ?? { topic: o.question.scope_label, subtopic: "", concept: "" }
        return o.grade ? (
          <EvaluationCard key={i} index={`· ${i + 1}`} question={o.question.question_text} answer={o.answer} grade={o.grade} knowledge={m} />
        ) : (
          <div key={i} className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            Answer {i + 1} could not be evaluated{o.error ? `: ${o.error}` : "."} Your text is preserved above in the session — retry from a new practice run.
          </div>
        )
      })}
    </motion.div>
  )
}
