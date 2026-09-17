import { motion, useReducedMotion } from "framer-motion"
import { AlertTriangle, BookOpenCheck, CheckCircle2, Lightbulb, ListChecks } from "lucide-react"
import { cn } from "@/lib/utils"

export type OEGrade = {
  score: number
  verdict: "pass" | "partial" | "fail"
  feedback: string
  strengths: string[]
  missing_points: string[]
  suggestions: string[]
}

export type KnowledgeRef = { topic: string; subtopic: string; concept: string }

export function GroundedChip() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-700">
      <BookOpenCheck size={12} /> Grounded in your project knowledge
    </span>
  )
}

function verdictStyle(v: OEGrade["verdict"]): string {
  if (v === "pass") return "border-green-200 bg-green-50 text-green-700"
  if (v === "partial") return "border-amber-200 bg-amber-50 text-amber-700"
  return "border-red-200 bg-red-50 text-red-700"
}

export function EvaluationCard({
  index,
  question,
  answer,
  grade,
  knowledge,
}: {
  index?: string | number
  question: string
  answer: string
  grade: OEGrade
  knowledge: KnowledgeRef
}) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="overflow-hidden rounded-xl border border-slate-200 bg-white"
    >
      <div className="border-b border-slate-100 bg-slate-50/60 px-5 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {index !== undefined ? `Open-Ended Evaluation ${index}` : "Open-Ended Evaluation"}
          </span>
          <GroundedChip />
        </div>
      </div>

      <div className="space-y-4 px-5 py-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Question</p>
          <p className="text-sm font-medium leading-relaxed text-slate-900">{question}</p>
        </div>

        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Your Answer</p>
          <p className="whitespace-pre-line rounded-lg border-l-2 border-indigo-300 bg-slate-50 px-3 py-2 text-sm leading-relaxed text-slate-700">
            {answer}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={cn(
              "font-mono-data text-4xl font-bold",
              grade.score >= 80 ? "text-green-600" : grade.score >= 50 ? "text-amber-600" : "text-red-600",
            )}
          >
            {grade.score}
          </span>
          <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold capitalize", verdictStyle(grade.verdict))}>
            {grade.verdict === "pass" ? "Passed" : grade.verdict === "partial" ? "Partial" : "Needs work"}
          </span>
        </div>

        {grade.strengths.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <CheckCircle2 size={13} className="text-green-600" /> What you got right
            </p>
            <ul className="space-y-1">
              {grade.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-green-500" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {grade.missing_points.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <AlertTriangle size={13} className="text-amber-600" /> What is missing
            </p>
            <ul className="space-y-1">
              {grade.missing_points.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-0.5 font-bold text-amber-500">!</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {grade.suggestions.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <Lightbulb size={13} className="text-indigo-500" /> What could be improved
            </p>
            <ul className="space-y-1">
              {grade.suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-0.5 text-indigo-500">→</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Feedback</p>
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600">{grade.feedback}</p>
        </div>

        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <ListChecks size={13} /> Knowledge Used
          </p>
          <div className="flex flex-wrap gap-1.5 text-xs">
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-medium text-slate-600">{knowledge.topic}</span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-medium text-slate-600">{knowledge.subtopic}</span>
            <span className="rounded-md border border-indigo-200 bg-indigo-50 px-2 py-1 font-medium text-indigo-700">{knowledge.concept}</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
