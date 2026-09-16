import { useEffect, useMemo, useState } from "react"
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronLeft,
  CircleAlert,
  Info,
  Loader2,
  PenLine,
  Search,
  XCircle,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Button, EmptyState, ErrorBox, LoadingState, SectionHeader } from "@/components/ui"
import { cn } from "@/lib/utils"
import type { ProjectTab } from "@/features/dashboard/Dashboard"

type Mode = "explain" | "open"
type Confidence = "low" | "medium" | "high"
type Stage = "pick" | "write" | "confidence" | "result"

type ConceptItem = { id: string; title: string; hint: string }

type GradeResult = {
  score: number
  verdict: "pass" | "partial" | "fail"
  feedback: string
}

function errText(status?: number, detail?: string): string {
  if (status === 429) return "Slow down — too many AI requests. Wait a moment and retry."
  if (status === 502) return "Assessment AI provider unavailable — nothing was saved. Retry when ready."
  if (status === 422) return detail ?? "This concept can't be assessed yet — pick a CORE target with source material."
  if (status === 404) return "Project or concept not found."
  return detail ?? "Assessment failed — nothing was saved."
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length
}

function verdictMeta(verdict: GradeResult["verdict"]): { label: string; cls: string; icon: React.ReactNode } {
  if (verdict === "pass")
    return { label: "Passed", cls: "border-green-200 bg-green-50 text-green-700", icon: <CheckCircle2 size={14} /> }
  if (verdict === "partial")
    return { label: "Partial", cls: "border-amber-200 bg-amber-50 text-amber-700", icon: <CircleAlert size={14} /> }
  return { label: "Needs work", cls: "border-red-200 bg-red-50 text-red-700", icon: <XCircle size={14} /> }
}

export function Assessments({
  projectId,
  onNavigate,
  onPracticeConcept,
  initialConceptId,
  onConsumed,
}: {
  projectId: string
  onNavigate?: (tab: ProjectTab) => void
  onPracticeConcept?: (conceptId: string) => void
  initialConceptId?: string | null
  onConsumed?: () => void
}) {
  const [concepts, setConcepts] = useState<ConceptItem[] | null>(null)
  const [treeFailed, setTreeFailed] = useState(false)
  const [mode, setMode] = useState<Mode>("explain")
  const [conceptId, setConceptId] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [stage, setStage] = useState<Stage>("pick")
  const [text, setText] = useState("")
  const [confidence, setConfidence] = useState<Confidence | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<(GradeResult & { conceptTitle: string }) | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ topics: { title: string; subtopics: { title: string; concepts: { id: string; title: string }[] }[] }[] }>(
        `/projects/${projectId}/knowledge/tree`,
      )
      .then((res) => {
        if (cancelled) return
        const items: ConceptItem[] = []
        for (const t of res.data.topics) {
          for (const s of t.subtopics) {
            for (const c of s.concepts) items.push({ id: c.id, title: c.title, hint: `${t.title} → ${s.title}` })
          }
        }
        setConcepts(items)
      })
      .catch(() => {
        if (!cancelled) setTreeFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  useEffect(() => {
    if (initialConceptId) {
      setConceptId(initialConceptId)
      setStage("write")
      onConsumed?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialConceptId])

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return concepts ?? []
    return (concepts ?? []).filter(
      (c) => c.title.toLowerCase().includes(needle) || c.hint.toLowerCase().includes(needle),
    )
  }, [search, concepts])

  const conceptTitle = concepts?.find((c) => c.id === conceptId)?.title ?? result?.conceptTitle ?? "Concept"
  const words = wordCount(text)
  const canSubmit = words >= 20 && !busy

  function begin(id: string) {
    setConceptId(id)
    setText("")
    setConfidence(null)
    setResult(null)
    setError(null)
    setStage("write")
  }

  async function evaluate() {
    if (!conceptId || !confidence || busy) return
    setBusy(true)
    setError(null)
    try {
      const path = mode === "explain" ? "explain-back" : "open-ended"
      const body =
        mode === "explain"
          ? { concept_id: conceptId, explanation_text: text.trim() }
          : { concept_id: conceptId, answer_text: text.trim() }
      const res = await apiClient.post<GradeResult>(`/projects/${projectId}/assessment/${path}`, body)
      setResult({ ...res.data, conceptTitle })
      setStage("result")
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setError(errText(status, detail))
    } finally {
      setBusy(false)
    }
  }

  function reset(full = false) {
    setText("")
    setConfidence(null)
    setResult(null)
    setError(null)
    if (full) {
      setConceptId(null)
      setStage("pick")
    } else {
      setStage("write")
    }
  }

  const go = (tab: ProjectTab) => onNavigate?.(tab)
  const practice = (id: string) => {
    if (onPracticeConcept) onPracticeConcept(id)
    else go("quiz")
  }

  return (
    <div className="mx-auto max-w-2xl">
      <SectionHeader title="Assessments" subtitle="Explain concepts in your own words — graded against your material" />

      {stage === "pick" && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
          <div className="mb-5 flex gap-1 rounded-xl border border-slate-200 bg-white p-1">
            {(
              [
                { id: "explain", label: "Explain it back" },
                { id: "open", label: "Open answer" },
              ] as const
            ).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setMode(m.id)}
                className={cn(
                  "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                  mode === m.id ? "bg-indigo-600 text-white" : "text-slate-500 hover:bg-slate-50",
                )}
              >
                <PenLine size={14} />
                {m.label}
              </button>
            ))}
          </div>
          <p className="mb-4 text-xs leading-relaxed text-slate-500">
            {mode === "explain"
              ? "Your explanation is graded and banked as applied-mastery evidence."
              : "Your answer is graded without banking evidence — a dry run."}
          </p>
          {concepts === null && !treeFailed && <LoadingState text="Loading concepts…" />}
          {treeFailed && (
            <ErrorBox message="Could not load concepts." onRetry={() => window.location.reload()} />
          )}
          {concepts !== null && concepts.length === 0 && (
            <EmptyState
              icon={<PenLine size={22} />}
              title="No concepts yet"
              hint="Upload a PDF and assessments unlock once it's processed."
            />
          )}
          {concepts !== null && concepts.length > 0 && (
            <>
              <div className="relative mb-2">
                <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search concepts…"
                  aria-label="Search concepts"
                  className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </div>
              <div className="max-h-64 space-y-1.5 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/50 p-2">
                {filtered.length === 0 && (
                  <p className="px-2 py-4 text-center text-xs text-slate-400">
                    No matches for “{search.trim()}” — try a different term.
                  </p>
                )}
                {filtered.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => begin(c.id)}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-50/40"
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">{c.title}</span>
                    <span className="block truncate text-xs text-slate-400">{c.hint}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {stage === "write" && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
          <button
            type="button"
            onClick={() => reset(true)}
            className="mb-4 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
          >
            <ChevronLeft size={14} /> All concepts
          </button>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {mode === "explain" ? "Explain it back" : "Open answer"}
          </div>
          <h2 className="text-lg font-semibold text-slate-900">{conceptTitle}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {mode === "explain"
              ? "Teach it in your own words — deeper than multiple choice."
              : "Answer freely — you'll get a grade without banking evidence."}
          </p>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Write your explanation here…"
            rows={8}
            className="mt-4 w-full rounded-xl border border-slate-200 p-4 text-sm leading-relaxed text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-300 focus:ring-2 focus:ring-indigo-50"
          />
          <div className="mt-2 flex items-center justify-between">
            <span className={cn("text-xs", words >= 20 ? "text-slate-400" : "text-amber-600")}>
              {words} words {words < 20 ? "· minimum 20 to submit" : ""}
            </span>
            <Button type="button" disabled={!canSubmit} onClick={() => setStage("confidence")}>
              Continue
            </Button>
          </div>
        </div>
      )}

      {stage === "confidence" && (
        <div className="mx-auto max-w-lg rounded-xl border border-slate-200 bg-white p-6 text-center sm:p-8">
          <h2 className="text-lg font-semibold text-slate-900">How confident are you?</h2>
          <p className="mt-1 text-sm text-slate-500">Rate your explanation of {conceptTitle} before grading.</p>
          <div className="mt-5 grid grid-cols-3 gap-2">
            {(["low", "medium", "high"] as const).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setConfidence(c)}
                className={cn(
                  "rounded-lg border px-3 py-3 text-sm font-medium capitalize transition-colors",
                  confidence === c
                    ? c === "low"
                      ? "border-red-300 bg-red-50 text-red-700"
                      : c === "medium"
                        ? "border-amber-300 bg-amber-50 text-amber-700"
                        : "border-green-300 bg-green-50 text-green-700"
                    : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50",
                )}
              >
                {c}
              </button>
            ))}
          </div>
          {error && (
            <div className="mt-4 text-left">
              <ErrorBox message={error} onRetry={() => setError(null)} retryLabel="Dismiss" />
            </div>
          )}
          <button
            type="button"
            onClick={() => void evaluate()}
            disabled={!confidence || busy}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            {busy ? "Evaluating…" : "Get AI evaluation"}
          </button>
          <button type="button" onClick={() => setStage("write")} className="mt-3 text-xs text-slate-400 hover:text-slate-600">
            ← Back to writing
          </button>
        </div>
      )}

      {stage === "result" && result && (
        <div>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-slate-900">Result</h2>
            <div className="flex gap-2">
              <button type="button" onClick={() => reset()} className="text-sm text-indigo-600 hover:underline">
                Re-attempt
              </button>
              <button type="button" onClick={() => reset(true)} className="text-sm text-indigo-600 hover:underline">
                Try another
              </button>
            </div>
          </div>

          <div className="mb-5 flex items-center gap-6 rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
            <div className="text-center">
              <div
                className={cn(
                  "font-mono-data text-5xl font-bold",
                  result.score >= 80 ? "text-green-600" : result.score >= 50 ? "text-amber-600" : "text-red-600",
                )}
              >
                {result.score}
              </div>
              <div className="mt-1 text-sm text-slate-500">Score</div>
            </div>
            <div className="flex-1">
              <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold", verdictMeta(result.verdict).cls)}>
                {verdictMeta(result.verdict).icon}
                {verdictMeta(result.verdict).label} · {conceptTitle}
              </span>
              {confidence && (
                <p className="mt-2 text-xs text-slate-500">
                  You rated {confidence} confidence{" "}
                  {result.score >= 80
                    ? confidence === "high"
                      ? "— well calibrated."
                      : "— you knew it better than you thought."
                    : confidence === "high"
                      ? "— higher than the grade suggests; revisit the material."
                      : "— honest self-assessment."}
                </p>
              )}
            </div>
          </div>

          <div className="mb-5 rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Info size={14} className="text-indigo-500" /> Understanding Analysis
            </div>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600">{result.feedback}</p>
            {mode === "explain" && (
              <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
                <Check size={12} className="text-green-500" /> Banked as applied-mastery evidence for {conceptTitle}.
              </p>
            )}
          </div>

          <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-5">
            <div className="mb-1 text-sm font-semibold text-slate-800">Suggested Next Step</div>
            <p className="mb-3 text-xs leading-relaxed text-slate-500">
              {result.verdict === "fail" && "Review the material, then prove it with a targeted quiz."}
              {result.verdict === "partial" && "Close the gap with a targeted quiz on this concept."}
              {result.verdict === "pass" && "Locked in — reinforce with flashcards or tackle the next concept."}
            </p>
            <div className="flex flex-wrap gap-2">
              {result.verdict === "fail" ? (
                <button type="button" onClick={() => go("materials")} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                  Review material
                </button>
              ) : result.verdict === "partial" ? (
                <button
                  type="button"
                  onClick={() => (conceptId ? practice(conceptId) : go("quiz"))}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Take a quiz
                </button>
              ) : (
                <button type="button" onClick={() => go("flashcards")} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                  Review flashcards
                </button>
              )}
              {conceptId && (
                <button
                  type="button"
                  onClick={() => practice(conceptId)}
                  className="rounded-lg border border-indigo-200 bg-white px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
                >
                  Quiz this concept
                </button>
              )}
            </div>
          </div>

          {result.verdict === "fail" && (
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-600" />
              <p className="text-xs leading-relaxed text-amber-800">
                Low score with explanation-based grading usually means a gap in the mental model, not just recall — re-read the source pages, then re-attempt.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
