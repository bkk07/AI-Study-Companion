import { useCallback, useEffect, useState } from "react"
import { Layers, Play, RotateCcw } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, Button, EmptyState, ErrorBox, LoadingState, ProgressBar } from "@/components/ui"
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
  { id: "again", label: "Again", hint: "Forgot it" },
  { id: "hard", label: "Hard", hint: "Recalled with effort" },
  { id: "good", label: "Good", hint: "Recalled confidently" },
  { id: "easy", label: "Easy", hint: "Trivial" },
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
      <div className="rounded-2xl border bg-card p-6 text-center shadow-soft">
        <p className="text-2xl font-extrabold tracking-tight text-gradient">Session complete</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Reviewed {done} of {total} cards — scheduling updated.
        </p>
        <Button type="button" variant="outline" onClick={onDone} className="mt-4">
          <RotateCcw className="h-4 w-4" /> Back to decks
        </Button>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <ProgressBar value={total ? (done / total) * 100 : 0} className="flex-1" />
        <span className="text-sm font-bold text-muted-foreground">
          {done + 1}/{total}
        </span>
        <Button type="button" variant="ghost" size="sm" onClick={onDone}>
          End session
        </Button>
      </div>
      <button
        type="button"
        onClick={() => setFlipped((f) => !f)}
        className="mt-3 block min-h-48 w-full rounded-2xl border bg-card p-6 text-center shadow-soft transition-all hover:border-violet-300"
      >
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-violet-600">
          {flipped ? "Answer — tap to hide" : "Tap to reveal"}
        </p>
        <p className={cn("mt-3 font-extrabold tracking-tight", flipped ? "text-lg" : "text-2xl")}>
          {flipped ? card.back : card.front}
        </p>
        {flipped && card.total_reviews > 0 && (
          <p className="mt-3 text-xs text-muted-foreground">
            Reviewed {card.total_reviews}× · {card.correct_reviews} recalled · every {card.interval_days}d
          </p>
        )}
      </button>
      {flipped ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {GRADES.map((g) => (
            <Button
              key={g.id}
              type="button"
              variant={g.id === "good" ? "primary" : "outline"}
              onClick={() => void grade(g.id)}
              disabled={grading}
              className="flex-col !gap-0.5 py-3"
            >
              <span className="font-bold">{g.label}</span>
              <span className="text-[11px] font-medium opacity-70">{g.hint}</span>
            </Button>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-center text-sm text-muted-foreground">
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
      <EmptyState
        icon={<Layers className="h-6 w-6" />}
        title="No flashcards yet"
        hint="Upload a PDF and decks build themselves from your learning targets."
      />
    )

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          <strong className="text-foreground">{dueCount}</strong> due for review
        </p>
        <Button
          type="button"
          onClick={() => void start()}
          disabled={starting !== null || dueCount === 0}
        >
          <Play className="h-4 w-4" /> {starting === "all" ? "Loading…" : "Review all due"}
        </Button>
      </div>
      <div className="mt-3 space-y-4">
        {topics.map((t) => (
          <div key={t.id}>
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t.title}
            </p>
            <ul className="mt-1.5 space-y-2">
              {t.subtopics.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between gap-3 rounded-2xl border bg-card p-4 shadow-soft"
                >
                  <div>
                    <p className="font-bold">{s.title}</p>
                    <p className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{s.core_count} learning targets</span>
                      <Badge tint="violet">auto deck</Badge>
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => void start(s.id)}
                    disabled={starting !== null}
                  >
                    <Play className="h-3.5 w-3.5" />{" "}
                    {starting === s.id ? "Loading…" : "Study"}
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
