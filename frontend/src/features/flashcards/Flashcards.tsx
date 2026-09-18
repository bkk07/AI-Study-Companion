import { useCallback, useEffect, useMemo, useState } from "react"
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  Layers,
  Play,
  Plus,
  RotateCcw,
  Search,
  Star,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { Button, EmptyState, ErrorBox, SectionHeader, Tag } from "@/components/ui"
import {
  AnimatedNumber,
  checkedConceptIds,
  KnowledgeTreeSelector,
  selectionCounts,
  TreeSkeleton,
} from "@/components/knowledge/KnowledgeTreeSelector"
import { cn } from "@/lib/utils"

type Card = {
  id: string
  concept_id: string
  front: string
  back: string
  repetitions: number
  lapses: number
  interval_days: number
  efactor: number
  next_review_at: string | null
  total_reviews: number
  correct_reviews: number
  due: boolean
}

export type { Card }

type LeafNode = { id: string; title: string }
type SubtopicNode = { id: string; title: string; core_count: number; concepts: LeafNode[] }
type TopicNode = { id: string; title: string; subtopics: SubtopicNode[] }

type CardState = "new" | "learning" | "mastered"

function cardState(c: Card): CardState {
  if (c.total_reviews === 0) return "new"
  if (c.repetitions >= 3) return "mastered"
  return "learning"
}

const GRADES = [
  { id: "again", label: "Again", hint: "Restart", cls: "border-red-200 bg-red-50 text-red-600 hover:bg-red-100" },
  { id: "hard", label: "Hard", hint: "Soon", cls: "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100" },
  { id: "good", label: "Good", hint: "Later", cls: "border-green-200 bg-green-50 text-green-700 hover:bg-green-100" },
  { id: "easy", label: "Easy", hint: "Much later", cls: "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100" },
] as const

function StudySession({
  projectId,
  initial,
  total,
  onDone,
}: {
  projectId: string
  initial: Card[]
  total: number
  onDone: () => void
}) {
  const [queue, setQueue] = useState<Card[]>(initial)
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [done, setDone] = useState(0)
  const [grading, setGrading] = useState(false)
  const [failed, setFailed] = useState(false)

  const card = queue[0] ?? null

  async function grade(id: string) {
    if (!card || grading) return
    setGrading(true)
    setFailed(false)
    try {
      await apiClient.post(`/projects/${projectId}/flashcards/${card.id}/review`, { grade: id })
      setQueue((q) => q.slice(1))
      setIndex((i) => i + 1)
      setDone((d) => d + 1)
      setFlipped(false)
    } catch {
      setFailed(true)
    } finally {
      setGrading(false)
    }
  }

  if (!card) {
    return (
      <div className="mx-auto max-w-2xl rounded-xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-xl font-semibold text-slate-900">Session complete</p>
        <p className="mt-1 text-sm text-slate-500">
          Reviewed {done} of {total} cards — scheduling updated.
        </p>
        <Button type="button" variant="secondary" onClick={onDone} className="mt-4">
          <RotateCcw size={14} /> Back to decks
        </Button>
      </div>
    )
  }

  return (
    <div className="flex min-h-full flex-col items-center bg-slate-50 px-8 py-10">
      <div className="mb-8 w-full max-w-xl">
        <div className="mb-3 flex items-center justify-between text-sm text-slate-500">
          <span className="font-medium">Review session</span>
          <span className="font-mono-data">Card {index + 1} / {total}</span>
        </div>
        <div className="h-1 overflow-hidden rounded-full bg-slate-200">
          <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(index / total) * 100}%` }} />
        </div>
      </div>

      <div className="card-flip-container w-full max-w-xl cursor-pointer" style={{ height: 280 }} onClick={() => setFlipped((f) => !f)}>
        <div className={cn("card-inner", flipped && "flipped")}>
          <div className="card-face flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-10 shadow-sm">
            <div className="mb-5 text-xs font-semibold uppercase tracking-wider text-slate-400">Question</div>
            <p className="text-center text-lg font-medium leading-relaxed text-slate-800">{card.front}</p>
            <p className="mt-6 text-xs text-slate-400">Click to reveal answer</p>
          </div>
          <div className="card-face card-back-face overflow-y-auto rounded-2xl border border-indigo-100 bg-indigo-50 p-8 shadow-sm">
            <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-indigo-400">Answer</div>
            <p className="text-base leading-relaxed text-slate-700">{card.back}</p>
            {card.total_reviews > 0 && (
              <div className="mt-5 w-full border-t border-indigo-100 pt-4">
                <p className="text-xs text-slate-400">
                  Reviewed {card.total_reviews}× · {card.correct_reviews} recalled · every {card.interval_days}d
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className={cn("mt-8 transition-opacity", flipped ? "opacity-100" : "pointer-events-none opacity-0")}>
        <p className="mb-3 text-center text-xs font-medium uppercase tracking-wide text-slate-500">
          How well did you recall this?
        </p>
        <div className="flex gap-3">
          {GRADES.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => void grade(g.id)}
              disabled={grading}
              className={cn("rounded-xl border px-5 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50", g.cls)}
            >
              {g.label}
              <div className="mt-0.5 text-xs font-normal opacity-60">{g.hint}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8 flex items-center gap-4">
        <button
          type="button"
          onClick={() => setFlipped(false)}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 p-2 text-xs text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
        >
          <RotateCcw size={12} />Reset
        </button>
        <button type="button" onClick={onDone} className="ml-4 text-xs text-slate-400 transition-colors hover:text-slate-600">
          Exit
        </button>
      </div>
      {failed && (
        <div className="mt-4 w-full max-w-xl">
          <ErrorBox message="Grade not saved — retry." onRetry={() => setFailed(false)} retryLabel="Dismiss" />
        </div>
      )}
    </div>
  )
}

type SubView = "dashboard" | "study" | "library" | "generate"

export function Flashcards({
  projectId,
  initialDeck,
  onDeckConsumed,
}: {
  projectId: string
  initialDeck?: { cards: Card[] } | null
  onDeckConsumed?: () => void
}) {
  const [topics, setTopics] = useState<TopicNode[] | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [dueCount, setDueCount] = useState(0)
  const [failed, setFailed] = useState(false)
  const [starting, setStarting] = useState<string | null>(null)
  const [building, setBuilding] = useState(false)
  const [buildResult, setBuildResult] = useState<{ created: number; total: number } | null>(null)
  const [session, setSession] = useState<{ cards: Card[]; total: number } | null>(null)
  const [view, setView] = useState<SubView>("dashboard")
  const [filter, setFilter] = useState("all")
  const [search, setSearch] = useState("")
  const [genChecked, setGenChecked] = useState<Set<string>>(new Set())

  const load = useCallback(async () => {
    setFailed(false)
    try {
      const [tree, list] = await Promise.all([
        apiClient.get<{ topics: TopicNode[] }>(`/projects/${projectId}/knowledge/tree`),
        apiClient.get<{ cards: Card[]; due_count: number }>(`/projects/${projectId}/flashcards?limit=100`),
      ])
      setTopics(tree.data.topics)
      setCards(list.data.cards)
      setDueCount(list.data.due_count)
    } catch {
      setFailed(true)
    }
  }, [projectId])

  useEffect(() => {
    setSession(null)
    setView("dashboard")
    void load()
  }, [load])

  // Direct entry from the tutor plan flow: jump straight into the deck.
  useEffect(() => {
    if (initialDeck && initialDeck.cards.length > 0) {
      setSession({ cards: initialDeck.cards, total: initialDeck.cards.length })
      setView("study")
      onDeckConsumed?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialDeck])

  const conceptTitles = useMemo(() => {
    const map = new Map<string, string>()
    for (const t of topics ?? []) {
      for (const s of t.subtopics) {
        for (const c of s.concepts ?? []) map.set(c.id, c.title)
      }
    }
    for (const c of cards) {
      if (!map.has(c.concept_id)) map.set(c.concept_id, "Concept")
    }
    return map
  }, [topics, cards])

  const stats = useMemo(() => {
    let fresh = 0, learning = 0, mastered = 0
    for (const c of cards) {
      const s = cardState(c)
      if (s === "new") fresh += 1
      else if (s === "learning") learning += 1
      else mastered += 1
    }
    // dueCount comes from the API (project-wide); the rest from the fetched page.
    return { total: cards.length, due: dueCount, fresh, learning, mastered }
  }, [cards, dueCount])

  async function start(subtopicId?: string) {
    const key = subtopicId ?? "all"
    setStarting(key)
    try {
      // Decks are idempotent — ensure cards exist before fetching due cards.
      await apiClient.post(`/projects/${projectId}/flashcards/decks`, subtopicId ? { subtopic_id: subtopicId } : {})
      const res = await apiClient.get<{ cards: Card[] }>(
        `/projects/${projectId}/flashcards?due_only=true&limit=50${subtopicId ? `&subtopic_id=${subtopicId}` : ""}`,
      )
      if (res.data.cards.length > 0) {
        setSession({ cards: res.data.cards, total: res.data.cards.length })
        setView("study")
      }
    } catch {
      setFailed(true)
    } finally {
      setStarting(null)
      void load()
    }
  }

  const genCounts = useMemo(() => selectionCounts(topics ?? [], genChecked), [topics, genChecked])
  const genConceptList = useMemo(
    () => checkedConceptIds(topics ?? [], genChecked),
    [topics, genChecked],
  )
  const totalConcepts = useMemo(
    () => (topics ?? []).reduce((n, t) => n + t.subtopics.reduce((m, s) => m + s.concepts.length, 0), 0),
    [topics],
  )
  const genValid = genConceptList.length > 0

  async function buildDeck() {
    if (building || !genValid) return
    setBuilding(true)
    setBuildResult(null)
    try {
      // Entire project selected → project scope ({}); otherwise the explicit
      // concept_ids multi-select (same backend path as the tutor flow).
      const body =
        genConceptList.length >= totalConcepts && totalConcepts > 0
          ? {}
          : { concept_ids: genConceptList }
      const res = await apiClient.post<{ created: number; total: number }>(`/projects/${projectId}/flashcards/decks`, body)
      setBuildResult(res.data)
      await load()
    } catch {
      setFailed(true)
    } finally {
      setBuilding(false)
    }
  }

  const libraryCards = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return cards.filter((c) => {
      const state = cardState(c)
      const matchState =
        filter === "all" ? true : filter === "due" ? c.due : state === filter
      const title = conceptTitles.get(c.concept_id) ?? ""
      const matchSearch =
        !needle || c.front.toLowerCase().includes(needle) || title.toLowerCase().includes(needle)
      return matchState && matchSearch
    })
  }, [cards, filter, search, conceptTitles])

  const builtPreview = useMemo(() => {
    if (!buildResult) return []
    if (genConceptList.length >= totalConcepts || genConceptList.length === 0) {
      return cards.slice(0, 10)
    }
    const allowed = new Set(genConceptList)
    return cards.filter((c) => allowed.has(c.concept_id)).slice(0, 10)
  }, [buildResult, cards, genConceptList, totalConcepts])

  if (session) {
    return (
      <StudySession
        projectId={projectId}
        initial={session.cards}
        total={session.total}
        onDone={() => {
          setSession(null)
          setView("dashboard")
          void load()
        }}
      />
    )
  }

  if (failed) return <ErrorBox message="Could not load flashcards." onRetry={() => void load()} />
  if (!topics) {
    return (
      <div className="mx-auto max-w-5xl">
        <div className="mb-6">
          <SectionHeader title="Flashcards" subtitle="Spaced repetition review of your concepts" />
        </div>
        <TreeSkeleton rows={3} />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <SectionHeader title="Flashcards" subtitle="Spaced repetition review of your concepts" />
        <div className="flex shrink-0 gap-2">
          {view !== "dashboard" ? (
            <Button variant="secondary" size="sm" onClick={() => setView("dashboard")}>
              <ChevronLeft size={14} />Back
            </Button>
          ) : (
            <>
              <Button variant="secondary" size="sm" onClick={() => setView("library")}>Library</Button>
              <Button variant="secondary" size="sm" onClick={() => { setBuildResult(null); setView("generate") }}>
                <Plus size={14} />Generate
              </Button>
            </>
          )}
        </div>
      </div>

      {view === "dashboard" && (
        <>
          {topics.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white">
              <EmptyState
                icon={<Layers size={24} />}
                title="No flashcards yet"
                hint="Upload a PDF and decks build themselves from your learning targets."
              />
            </div>
          ) : (
            <>
              <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
                {[
                  { label: "Total cards", value: stats.total, color: "text-slate-800" },
                  { label: "Due today", value: stats.due, color: "text-indigo-600" },
                  { label: "New", value: stats.fresh, color: "text-blue-600" },
                  { label: "Learning", value: stats.learning, color: "text-amber-600" },
                  { label: "Mastered", value: stats.mastered, color: "text-green-600" },
                ].map((s) => (
                  <div key={s.label} className="rounded-xl border border-slate-200 bg-white px-4 py-4 text-center">
                    <div className={`font-mono-data text-2xl font-bold ${s.color}`}>{s.value}</div>
                    <div className="mt-1 text-xs text-slate-500">{s.label}</div>
                  </div>
                ))}
              </div>

              {stats.due > 0 ? (
                <div className="flex items-center gap-8 rounded-xl border border-slate-200 bg-white p-8">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-indigo-100 bg-indigo-50">
                    <CreditCard size={28} className="text-indigo-600" />
                  </div>
                  <div className="flex-1">
                    <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Continue Review</div>
                    <h2 className="text-xl font-semibold text-slate-900">{stats.due} cards due</h2>
                    <p className="mt-1 text-sm text-slate-500">Complete your spaced repetition review to maintain mastery</p>
                  </div>
                  <Button type="button" onClick={() => void start()} disabled={starting !== null}>
                    <Play size={15} /> {starting === "all" ? "Loading…" : "Start Review"}
                  </Button>
                </div>
              ) : (
                <div className="rounded-xl border border-slate-200 bg-white">
                  <EmptyState
                    icon={<Star size={22} />}
                    title="All caught up!"
                    hint={stats.total === 0 ? "Build a deck below to create cards from your learning targets." : "No cards are due today. Come back tomorrow or review a deck below."}
                  />
                </div>
              )}

              {cards.length > 0 && (
                <div className="mt-8">
                  <div className="mb-3 text-sm font-semibold text-slate-700">Recent flashcards</div>
                  <div className="space-y-2">
                    {cards.slice(0, 5).map((card) => {
                      const state = cardState(card)
                      return (
                        <div key={card.id} className="flex items-center gap-4 rounded-lg border border-slate-200 bg-white px-4 py-3">
                          <div className={cn("h-1.5 w-1.5 shrink-0 rounded-full", state === "mastered" ? "bg-green-500" : state === "learning" ? "bg-amber-400" : "bg-blue-400")} />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm text-slate-700">{card.front}</p>
                            <p className="mt-0.5 text-xs text-slate-400">{conceptTitles.get(card.concept_id)}</p>
                          </div>
                          <Tag color={state === "mastered" ? "green" : state === "learning" ? "amber" : "indigo"}>{state}</Tag>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      {view === "library" && (
        <div>
          <div className="mb-5 flex items-center gap-3">
            <div className="relative max-w-xs flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm text-slate-700 outline-none placeholder:text-slate-400 focus:border-indigo-400"
                placeholder="Search flashcards…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex gap-1 overflow-x-auto">
              {["all", "due", "new", "learning", "mastered"].map((f) => (
                <button
                  key={f}
                  type="button"
                  className={cn("rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors", filter === f ? "bg-indigo-600 text-white" : "text-slate-500 hover:bg-slate-100")}
                  onClick={() => setFilter(f)}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
          {libraryCards.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white">
              <EmptyState icon={<Search size={22} />} title="No cards match" hint="Try a different search term or filter." />
            </div>
          ) : (
            <div className="space-y-2">
              {libraryCards.map((card) => {
                const state = cardState(card)
                return (
                  <div key={card.id} className="rounded-xl border border-slate-200 bg-white px-5 py-4 transition-colors hover:border-slate-300">
                    <div className="flex items-start gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="mb-1 text-xs text-slate-400">{conceptTitles.get(card.concept_id)}</div>
                        <p className="line-clamp-2 text-sm font-medium text-slate-800">{card.front}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Tag color={state === "mastered" ? "green" : state === "learning" ? "amber" : "indigo"}>{state}</Tag>
                        <button
                          type="button"
                          title="Study this card"
                          onClick={() => {
                            setSession({ cards: [card], total: 1 })
                            setView("study")
                          }}
                          className="rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
                        >
                          <Play size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 flex gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1"><Clock size={11} />Reviewed {card.total_reviews}×</span>
                      {card.next_review_at && (
                        <span className="flex items-center gap-1"><ChevronRight size={11} />Next: {new Date(card.next_review_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {view === "generate" && (
        <div>
          <div className="rounded-xl border border-slate-200 bg-white p-8">
            <h2 className="text-lg font-semibold text-slate-900">Generate Flashcards</h2>
            <p className="mt-1 text-sm text-slate-500">
              Select topics, subtopics, or individual concepts — one recall card per CORE concept, no duplicates.
            </p>

            <div className="mt-4">
              <KnowledgeTreeSelector topics={topics} checked={genChecked} onChange={setGenChecked} />
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-4" aria-live="polite">
              <p className="text-sm text-slate-600">
                Selected knowledge ·{" "}
                <strong className="font-semibold text-slate-900">
                  <AnimatedNumber value={genCounts.topics} /> Topic{genCounts.topics === 1 ? "" : "s"}
                </strong>
                {" · "}
                <strong className="font-semibold text-slate-900">
                  <AnimatedNumber value={genCounts.subtopics} /> Subtopic{genCounts.subtopics === 1 ? "" : "s"}
                </strong>
                {" · "}
                <strong className="font-semibold text-slate-900">
                  <AnimatedNumber value={genCounts.concepts} /> Concept{genCounts.concepts === 1 ? "" : "s"}
                </strong>
              </p>
            </div>

            <button
              type="button"
              onClick={() => void buildDeck()}
              disabled={building || !genValid}
              className="mt-4 flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {building && <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
              {building ? "Building…" : "Generate"}
            </button>
            {!genValid && (
              <p className="mt-2 text-xs text-slate-400">Select at least one concept to generate.</p>
            )}

            {buildResult && (
              <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                Built {buildResult.created} new card{buildResult.created === 1 ? "" : "s"} — {buildResult.total} total in project.
              </div>
            )}
          </div>

          {buildResult && builtPreview.length > 0 && (
            <div className="mt-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">Preview — {builtPreview.length} cards</h2>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    setSession({ cards: builtPreview, total: builtPreview.length })
                    setView("study")
                  }}
                  disabled={builtPreview.length === 0}
                >
                  <Play size={14} /> Study now
                </Button>
              </div>
              <div className="space-y-4">
                {builtPreview.map((c) => (
                  <div key={c.id} className="rounded-xl border border-slate-200 bg-white p-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="mb-1.5 text-xs font-medium text-slate-400">Front</div>
                        <p className="text-sm leading-relaxed text-slate-700">{c.front}</p>
                      </div>
                      <div className="border-l border-slate-100 pl-4">
                        <div className="mb-1.5 text-xs font-medium text-slate-400">Back</div>
                        <p className="line-clamp-4 text-sm leading-relaxed text-slate-600">{c.back}</p>
                      </div>
                    </div>
                    <div className="mt-3 border-t border-slate-50 pt-3 text-xs text-slate-400">
                      {conceptTitles.get(c.concept_id)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
