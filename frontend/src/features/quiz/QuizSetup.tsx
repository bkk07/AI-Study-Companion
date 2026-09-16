import { useEffect, useMemo, useState } from "react"
import { Check, Info, Play, Search, Sparkles } from "lucide-react"
import apiClient from "@/lib/axios"
import { EmptyState, LoadingState, SectionHeader } from "@/components/ui"
import { cn } from "@/lib/utils"

export type QuizScope = "project" | "topic" | "subtopic" | "concept"

export type QuizMode = "practice" | "exam"

export type QuizStartPayload = {
  scope: QuizScope
  topicId?: string
  subtopicId?: string
  conceptId?: string
  numQuestions: number
  mode: QuizMode
}

type Leaf = { id: string; title: string }
type SubNode = { id: string; title: string; concepts: Leaf[] }
type TopicNode = { id: string; title: string; subtopics: SubNode[] }

type Candidate = {
  concept_id: string
  name: string
  reasoning: string
}

type Recommendations = { items: Candidate[]; fallback: Candidate | null }

const SCOPES: { id: QuizScope; label: string }[] = [
  { id: "project", label: "Entire Project" },
  { id: "topic", label: "Topic" },
  { id: "subtopic", label: "Subtopic" },
  { id: "concept", label: "Concept" },
]

const COUNTS = [5, 10, 20]

function ScopePicker({
  label,
  searchPlaceholder,
  items,
  selectedId,
  onSelect,
}: {
  label: string
  searchPlaceholder: string
  items: { id: string; title: string; hint?: string }[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const [q, setQ] = useState("")
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    if (!needle) return items
    return items.filter(
      (i) =>
        i.title.toLowerCase().includes(needle) ||
        (i.hint ?? "").toLowerCase().includes(needle),
    )
  }, [q, items])

  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      <div className="relative mb-2">
        <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={searchPlaceholder}
          aria-label={`Search ${label.toLowerCase()}`}
          className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
      </div>
      <div className="max-h-48 space-y-1.5 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/50 p-2">
        {filtered.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-slate-400">
            No matches for “{q.trim()}” — try a different term.
          </p>
        )}
        {filtered.map((item) => {
          const active = selectedId === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                active
                  ? "border-indigo-500 bg-indigo-50 text-indigo-800"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300",
              )}
            >
              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                  active ? "bg-indigo-600 text-white" : "bg-slate-100 text-transparent",
                )}
              >
                <Check size={12} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{item.title}</span>
                {item.hint && <span className="block truncate text-xs opacity-70">{item.hint}</span>}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function QuizSetup({
  projectId,
  busy,
  onStart,
  initialConceptId,
  onConsumed,
}: {
  projectId: string
  busy: boolean
  onStart: (payload: QuizStartPayload) => void
  initialConceptId?: string | null
  onConsumed?: () => void
}) {
  const [scope, setScope] = useState<QuizScope>("project")
  const [qCount, setQCount] = useState(5)
  const [quizMode, setQuizMode] = useState<QuizMode>("practice")
  const [topics, setTopics] = useState<TopicNode[] | null>(null)
  const [treeFailed, setTreeFailed] = useState(false)
  const [topicId, setTopicId] = useState<string | null>(null)
  const [subId, setSubId] = useState<string | null>(null)
  const [conceptId, setConceptId] = useState<string | null>(null)
  const [recs, setRecs] = useState<Recommendations | null>(null)

  // Deep link from Dashboard ("Study this"): preselect the concept scope.
  useEffect(() => {
    if (initialConceptId) {
      setScope("concept")
      setConceptId(initialConceptId)
      onConsumed?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialConceptId])

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ topics: TopicNode[] }>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (!cancelled) setTopics(res.data.topics)
      })
      .catch(() => {
        if (!cancelled) setTreeFailed(true)
      })
    apiClient
      .get<Recommendations>(`/projects/${projectId}/practice/recommendations?limit=3`)
      .then((res) => {
        if (!cancelled) setRecs(res.data)
      })
      .catch(() => {
        if (!cancelled) setRecs({ items: [], fallback: null })
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  const topicItems = useMemo(
    () =>
      (topics ?? []).map((t) => ({
        id: t.id,
        title: t.title,
        hint: `${t.subtopics.length} subtopics`,
      })),
    [topics],
  )
  const subItems = useMemo(
    () =>
      (topics ?? []).flatMap((t) =>
        t.subtopics.map((s) => ({ id: s.id, title: s.title, hint: t.title })),
      ),
    [topics],
  )
  const conceptItems = useMemo(() => {
    const out: { id: string; title: string; hint?: string }[] = []
    for (const t of topics ?? []) {
      for (const s of t.subtopics) {
        for (const c of s.concepts) {
          out.push({ id: c.id, title: c.title, hint: `${t.title} → ${s.title}` })
        }
      }
    }
    return out
  }, [topics])

  const valid =
    scope === "project" ||
    (scope === "topic" && topicId !== null) ||
    (scope === "subtopic" && subId !== null) ||
    (scope === "concept" && conceptId !== null)

  const start = () => {
    if (!valid || busy) return
    onStart({ scope, topicId: topicId ?? undefined, subtopicId: subId ?? undefined, conceptId: conceptId ?? undefined, numQuestions: qCount, mode: quizMode })
  }

  const recommended = recs ? [...recs.items.slice(0, 2), ...(recs.fallback ? [recs.fallback] : [])].slice(0, 3) : null

  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <SectionHeader title="Adaptive Quiz" subtitle="Questions are selected based on your mastery evidence" />

      {recommended && recommended.length > 0 && (
        <div className="mb-5 rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-500">
            <Sparkles size={12} /> Recommended
          </p>
          <div className="space-y-2">
            {recommended.map((c) => (
              <div key={c.concept_id} className="flex items-center gap-3 rounded-lg border border-indigo-100 bg-white px-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900">{c.name}</p>
                  <p className="line-clamp-2 text-xs text-slate-500">{c.reasoning}</p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    onStart({ scope: "concept", conceptId: c.concept_id, numQuestions: qCount, mode: quizMode })
                  }
                  className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Play size={12} /> Quiz me
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-8">
        <div>
          <label className="mb-2.5 block text-sm font-medium text-slate-700">Quiz scope</label>
          <div className="flex flex-wrap gap-2">
            {SCOPES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setScope(s.id)}
                className={cn(
                  "rounded-lg border px-3 py-1.5 text-sm capitalize transition-colors",
                  scope === s.id
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-slate-200 text-slate-600 hover:border-slate-300",
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {scope !== "project" && (
          <div>
            {topics === null && !treeFailed && <LoadingState text="Loading topics…" />}
            {treeFailed && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
                Could not load topics — upload material first, or try the Entire Project scope.
              </p>
            )}
            {topics !== null && topics.length === 0 && (
              <EmptyState
                icon={<Search size={20} />}
                title="No topics yet"
                hint="Upload a PDF and scoped quizzes unlock once it's processed."
              />
            )}
            {topics !== null && topics.length > 0 && scope === "topic" && (
              <ScopePicker
                label="Topic"
                searchPlaceholder="Search topics…"
                items={topicItems}
                selectedId={topicId}
                onSelect={setTopicId}
              />
            )}
            {topics !== null && topics.length > 0 && scope === "subtopic" && (
              <ScopePicker
                label="Subtopic"
                searchPlaceholder="Search subtopics…"
                items={subItems}
                selectedId={subId}
                onSelect={setSubId}
              />
            )}
            {topics !== null && topics.length > 0 && scope === "concept" && (
              <ScopePicker
                label="Concept"
                searchPlaceholder="Search concepts…"
                items={conceptItems}
                selectedId={conceptId}
                onSelect={setConceptId}
              />
            )}
          </div>
        )}

        <div>
          <label className="mb-2.5 block text-sm font-medium text-slate-700">Number of questions</label>
          <div className="flex gap-2">
            {COUNTS.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setQCount(n)}
                className={cn(
                  "rounded-lg border px-5 py-1.5 text-sm transition-colors",
                  qCount === n
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-slate-200 text-slate-600 hover:border-slate-300",
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2.5 block text-sm font-medium text-slate-700">Mode</label>
          <div className="flex gap-2">
            {(
              [
                { id: "practice", label: "Practice", hint: "Learn as you go" },
                { id: "exam", label: "Exam", hint: "Test conditions" },
              ] as const
            ).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setQuizMode(m.id)}
                className={cn(
                  "flex-1 rounded-lg border px-4 py-2 text-left transition-colors",
                  quizMode === m.id
                    ? "border-indigo-500 bg-indigo-50"
                    : "border-slate-200 hover:border-slate-300",
                )}
              >
                <span className={cn("block text-sm font-medium", quizMode === m.id ? "text-indigo-700" : "text-slate-600")}>
                  {m.label}
                </span>
                <span className="block text-xs text-slate-400">{m.hint}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Difficulty</label>
          <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 text-sm text-slate-500">
            Adaptive — questions are chosen based on mastery evidence and detected mismatches
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Info size={12} />
          Estimated time: {(qCount * 1.5).toFixed(1).replace(/\.0$/, "")} minutes
        </div>

        {!valid && (
          <p className="text-xs text-slate-400">
            {scope === "topic" && "Pick a topic above to start."}
            {scope === "subtopic" && "Pick a subtopic above to start."}
            {scope === "concept" && "Pick a concept above — or use a Recommended quiz."}
          </p>
        )}

        <button
          type="button"
          onClick={start}
          disabled={!valid || busy}
          className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Preparing quiz…" : "Start Quiz"}
        </button>
      </div>
    </div>
  )
}
