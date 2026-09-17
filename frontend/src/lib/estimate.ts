/** Minutes learners typically spend per question type. Display-only estimates. */
export const MINUTES_PER_MCQ = 1.5
export const MINUTES_PER_OPEN_ENDED = 4

/** Single time-estimate formula shared by Quiz, Practice, and Open-Ended pages. */
export function estimateMinutes({ mcq = 0, openEnded = 0 }: { mcq?: number; openEnded?: number }): string {
  const mins = Math.max(1, Math.round(mcq * MINUTES_PER_MCQ + openEnded * MINUTES_PER_OPEN_ENDED))
  return `~${mins} min`
}
