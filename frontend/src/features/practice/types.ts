import type { OEGrade } from "@/components/knowledge/EvaluationCard"

export type PracticeLevel = "adaptive" | "easy" | "medium" | "hard"

export type McqItem = {
  id: string
  question_text: string
  options: string[]
  difficulty: string
  concept_id: string
}

export type OeItem = {
  question_text: string
  concept_id: string
  scope_label: string
  difficulty: string | null
}

export type McqResult = {
  question: McqItem
  selected: number | null
  isCorrect: boolean
  correctIndex: number
}

export type OeResult = {
  question: OeItem
  answer: string
  grade: OEGrade | null
  error: string | null
}

export type ConceptMeta = Map<string, { topic: string; subtopic: string; concept: string }>

export const EVAL_STEPS = [
  "Analyzing your answer...",
  "Retrieving relevant knowledge...",
  "Comparing against project knowledge...",
  "Generating feedback...",
]
