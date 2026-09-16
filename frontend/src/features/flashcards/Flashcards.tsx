import { useCallback, useEffect, useState } from "react"
import { CreditCard, Layers, Play, RotateCcw } from "lucide-react"
import apiClient from "@/lib/axios"
import { Button, EmptyState, ErrorBox, LoadingState, SectionHeader, StatCard } from "@/components/ui"
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

type SubtopicNode = { id: string; title: string; core_count: number }
type TopicNode = { id: string; title: string; subtopics: SubtopicNode[] }

const GRADES = [
  { id: "again", label: "Again", hint: "+1d" },
  { id: "hard", label: "Hard", hint: "+3d" },
  { id: "good", label: "Good", hint: "+4d" },
  { id: "easy", label: "Easy", hint: "+7d" },
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
    <div className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center gap-3">
        <span className="text-sm font-medium text-slate-600">Card {done + 1}/{total}</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(done / total) * 100}%` }} />
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onDone}>
          Exit
        </Button>
      </div>
      <div className="card-flip-container" style={{ height: 280 }}>
        <div className={cn("card-inner", flipped && "flipped")}>
          <button
            type="button"
            onClick={() => setFlipped((f) => !f)}
            className="card-face flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white p-8 text-center"
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Question</p>
            <p className="mt-3 text-xl font-semibold text-slate-900">{card.front}</p>
            <p className="mt-4 text-xs text-slate-400">Click to flip</p>
          </button>
          <button
            type="button"
            onClick={() => setFlipped((f) => !f)}
            className="card-face card-back-face flex-col items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 p-8 text-center"
            style={{ display: "flex" }}
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400">Answer</p>
            <p className="mt-3 text-lg font-medium text-slate-900">{card.back}</p>
            {card.total_reviews > 0 && (
              <p className="mt-3 text-xs text-slate-500">
                Reviewed {card.total_reviews}× · {card.correct_reviews} recalled · every {card.interval_days}d
              </p>
            )}
          </button>
        </div>
      </div>
      {flipped ? (
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {GRADES.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => void grade(g.id)}
              disabled={grading}
              className={cn(
                "rounded-xl border px-3 py-3 text-center transition-colors disabled:opacity-50",
                g.id === "good"
                  ? "border-indigo-600 bg-indigo-600 text-white hover:bg-indigo-700"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
              )}
            >
              <span className="block text-sm font-semibold">{g.label}</span>
              <span className="block text-xs opacity-70">{g.hint}</span>
            </button>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-center text-sm text-slate-500">
          Recall the answer, then flip and grade yourself honestly.
        </p>
      )}
      {failed && (
        <div className="mt-3">
          <ErrorBox message="Grade not saved — retry." onRetry={() => setFailed(false)} retryLabel="Dismiss" />
        </div>
      )}
    </div>
  )
}

export function Flashcards({ projectId }: { projectId: string }) {
  const [topics, setTopics] = useState<TopicNode[] | null>(null)
  const [dueCount, setDueCount] = useState(0)
  const [failed, setFailed] = useState(false)
  const [starting, setStarting] = useState<string | null>(null)
  const [session, setSession] = useState<{ cards: Card[]; total: number } | null>(null)

  const load = useCallback(async () => {
    setFailed(false)
    try {
      const [tree, cards] = await Promise.all([
        apiClient.get<{ topics: TopicNode[] }>(`/projects/${projectId}/knowledge/tree`),
        apiClient.get<{ cards: Card[]; due_count: number }>(
          `/projects/${projectId}/flashcards?limit=1`,
        ),
      ])
      setTopics(tree.data.topics)
      setDueCount(cards.data.due_count)
    } catch {
      setFailed(true)
    }
  }, [projectId])

  useEffect(() => {
    setSession(null)
    void load()
  }, [load])

  async function start(subtopicId?: string) {
    setStarting(subtopicId ?? "all")
    try {
      if (subtopicId) {
        await apiClient.post(`/projects/${projectId}/flashcards/decks`, {
          subtopic_id: subtopicId,
        })
      }
      const res = await apiClient.get<{ cards: Card[] }>(
        `/projects/${projectId}/flashcards?due_only=true&limit=50${
          subtopicId ? `&subtopic_id=${subtopicId}` : ""
        }`,
      )
      if (res.data.cards.length > 0) {
        setSession({ cards: res.data.cards, total: res.data.cards.length })
      }
    } catch {
      setFailed(true)
    } finally {
      setStarting(null)
      void load()
    }
  }

  if (session) {
    return (
      <StudySession
        projectId={projectId}
        initial={session.cards}
        total={session.total}
        onDone={() => {
          setSession(null)
          void load()
        }}
      />
    )
  }

  if (failed)
    return <ErrorBox message="Could not load flashcards." onRetry={() => void load()} />
  if (!topics) return <LoadingState text="Loading decks…" />
  if (topics.length === 0)
    return (
      <div className="rounded-xl border border-slate-200 bg-white">
        <EmptyState
          icon={<Layers size={24} />}
          title="No flashcards yet"
          hint="Upload a PDF and decks build themselves from your learning targets."
        />
      </div>
    )

  return (
    <div className="mx-auto max-w-5xl">
      <SectionHeader
        title="Flashcards"
        subtitle="Spaced repetition grounded in your concepts"
        action={
          <Button type="button" variant="secondary" size="sm" onClick={() => void load()}>
            Library
          </Button>
        }
      />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatCard label="Due" value={dueCount} accent="indigo" icon={<CreditCard size={18} />} />
        <StatCard label="Topics" value={topics.length} accent="slate" icon={<Layers size={18} />} />
        <StatCard label="Decks" value={topics.reduce((n, t) => n + t.subtopics.length, 0)} accent="slate" icon={<Layers size={18} />} />
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <Play size={18} />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-slate-900">Continue Review</h3>
            <p className="text-sm text-slate-500">{dueCount} cards due based on spaced repetition</p>
          </div>
          <Button
            type="button"
            onClick={() => void start()}
            disabled={starting !== null || dueCount === 0}
          >
            <Play size={14} /> {starting === "all" ? "Loading…" : "Start"}
          </Button>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {topics.map((t) => (
          <div key={t.id}>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
              {t.title}
            </p>
            <div className="space-y-2">
              {t.subtopics.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4"
                >
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{s.title}</p>
                    <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
                      <span>{s.core_count} learning targets</span>
                      <span className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-xs text-slate-600">auto deck</span>
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => void start(s.id)}
                    disabled={starting !== null}
                  >
                    <Play size={14} />{" "}
                    {starting === s.id ? "Loading…" : "Study"}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
