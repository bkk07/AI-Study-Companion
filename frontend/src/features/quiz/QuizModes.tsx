import { useEffect, useState } from "react"
import { Compass, FolderTree, Play, Search as SearchIcon, Sparkles, Wand2 } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, Button, Card, EmptyState, Input, LoadingState, ProgressBar } from "@/components/ui"
import { cn } from "@/lib/utils"
import { ConceptDetail, statusTint } from "./ConceptDetail"

type Candidate = {
  concept_id: string
  name: string
  lo_type: string | null
  mastery: number | null
  status: string
  score: number | null
  reasoning: string
  fallback: boolean
}

type Recommendations = { items: Candidate[]; fallback: Candidate | null }

type Leaf = {
  id: string
  title: string
  lo_type: string
  mastery: number | null
  status: string
  practiced: boolean
}

type SubtopicNode = {
  id: string
  title: string
  core_count: number
  coverage: { mastery: number | null; practiced: number; total: number }
  concepts: Leaf[]
}

type TopicNode = {
  id: string
  title: string
  core_count: number
  coverage: { mastery: number | null; practiced: number; total: number }
  subtopics: SubtopicNode[]
}

type Hit = {
  id: string
  title: string
  lo_type: string
  importance: string
  topic: string
  subtopic: string
  page_start: number | null
  page_end: number | null
  mastery: number | null
  status: string | null
  practicable: boolean
}

type Mode = "recommended" | "browse" | "search"

function masteryLabel(mastery: number | null): string {
  return mastery === null ? "Not started" : `${Math.round(mastery)}%`
}

function PracticeButton({ onClick, disabled }: { onClick: () => void; disabled: boolean }) {
  return (
    <Button type="button" size="sm" onClick={onClick} disabled={disabled}>
      <Play className="h-3.5 w-3.5" /> Practice
    </Button>
  )
}

function CandidateCard({
  candidate,
  hero,
  busy,
  onPractice,
  onOpen,
}: {
  candidate: Candidate
  hero?: boolean
  busy: boolean
  onPractice: (id: string) => void
  onOpen: (id: string) => void
}) {
  return (
    <div className={cn(hero && "rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 p-5 text-white shadow-soft sm:p-6")}>
      {hero && (
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-white/80">
          <Sparkles className="h-4 w-4" /> Recommended for you
        </p>
      )}
      <div className={cn("flex flex-wrap items-center gap-2", hero ? "mt-2" : "mt-0")}>
        <button
          type="button"
          onClick={() => onOpen(candidate.concept_id)}
          className={cn(
            "text-left font-extrabold tracking-tight hover:underline",
            hero ? "text-xl text-white" : "text-base",
          )}
        >
          {candidate.name}
        </button>
        {candidate.lo_type && (
          <Badge tint={hero ? "muted" : "violet"} className={hero ? "bg-white/20 text-white ring-white/30" : undefined}>
            {candidate.lo_type}
          </Badge>
        )}
        <Badge tint={candidate.fallback ? "muted" : statusTint(candidate.status)}>
          {candidate.fallback ? "Get started" : candidate.status}
        </Badge>
      </div>
      {!candidate.fallback && (
        <div className={cn("mt-2 flex items-center gap-3", hero ? "text-white" : "")}>
          <ProgressBar value={candidate.mastery} className={cn("flex-1", hero && "bg-white/25")} />
          <span className={cn("text-sm font-extrabold", hero ? "text-white" : "text-gradient")}>
            {masteryLabel(candidate.mastery)}
          </span>
        </div>
      )}
      <p className={cn("mt-2 text-sm", hero ? "text-white/85" : "text-muted-foreground")}>
        {candidate.reasoning}
      </p>
      <div className="mt-3">
        {hero ? (
          <Button
            type="button"
            onClick={() => onPractice(candidate.concept_id)}
            disabled={busy}
            className="bg-white text-violet-700 shadow-none hover:bg-white/90 hover:shadow-none"
          >
            <Play className="h-4 w-4" /> Start Practice
          </Button>
        ) : (
          <PracticeButton onClick={() => onPractice(candidate.concept_id)} disabled={busy} />
        )}
      </div>
    </div>
  )
}

function Recommended({
  projectId,
  busy,
  onPractice,
  onOpen,
}: {
  projectId: string
  busy: boolean
  onPractice: (id: string) => void
  onOpen: (id: string) => void
}) {
  const [data, setData] = useState<Recommendations | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<Recommendations>(`/projects/${projectId}/practice/recommendations?limit=4`)
      .then((res) => {
        if (!cancelled) setData(res.data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  if (failed)
    return (
      <EmptyState
        icon={<Wand2 className="h-6 w-6" />}
        title="No practice targets yet"
        hint="Upload a PDF and recommendations unlock once it's processed."
      />
    )
  if (!data) return <LoadingState text="Finding what to practice…" />
  if (data.items.length === 0 && !data.fallback)
    return (
      <EmptyState
        icon={<Wand2 className="h-6 w-6" />}
        title="No practice targets yet"
        hint="Upload a PDF and recommendations unlock once it's processed."
      />
    )
  const [hero, ...rest] = data.items
  return (
    <div className="space-y-3">
      {hero && <CandidateCard candidate={hero} hero busy={busy} onPractice={onPractice} onOpen={onOpen} />}
      {data.fallback && (
        <CandidateCard candidate={data.fallback} hero busy={busy} onPractice={onPractice} onOpen={onOpen} />
      )}
      {rest.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Other recommendations
          </p>
          <div className="space-y-2">
            {rest.map((c) => (
              <Card key={c.concept_id} className="p-4">
                <CandidateCard candidate={c} busy={busy} onPractice={onPractice} onOpen={onOpen} />
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Browse({
  projectId,
  busy,
  onPractice,
  onOpen,
}: {
  projectId: string
  busy: boolean
  onPractice: (id: string) => void
  onOpen: (id: string) => void
}) {
  const [tree, setTree] = useState<TopicNode[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [topicId, setTopicId] = useState<string | null>(null)
  const [subId, setSubId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<{ topics: TopicNode[] }>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (!cancelled) setTree(res.data.topics)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  if (failed)
    return (
      <EmptyState
        icon={<FolderTree className="h-6 w-6" />}
        title="No topics yet"
        hint="Upload a PDF and browse unlocks once it's processed."
      />
    )
  if (!tree) return <LoadingState text="Loading topics…" />
  if (tree.length === 0)
    return (
      <EmptyState
        icon={<FolderTree className="h-6 w-6" />}
        title="No topics yet"
        hint="Upload a PDF and browse unlocks once it's processed."
      />
    )

  const topic = tree.find((t) => t.id === topicId) ?? null
  const sub = topic?.subtopics.find((s) => s.id === subId) ?? null

  if (!topic) {
    return (
      <ul className="space-y-2">
        {tree.map((t) => (
          <li key={t.id}>
            <button
              type="button"
              onClick={() => {
                setTopicId(t.id)
                setSubId(null)
              }}
              className="w-full rounded-2xl border bg-card p-4 text-left shadow-soft transition-all hover:border-violet-300"
            >
              <span className="font-bold">{t.title}</span>
              <span className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                <span>{t.core_count} core learning targets</span>
                <span>Mastery: {masteryLabel(t.coverage.mastery)}</span>
                <span>
                  Coverage: {t.coverage.practiced}/{t.coverage.total}
                </span>
              </span>
              <ProgressBar value={t.coverage.mastery} className="mt-2" />
            </button>
          </li>
        ))}
      </ul>
    )
  }

  if (!sub) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setTopicId(null)}
          className="text-sm font-semibold text-violet-700 hover:underline"
        >
          ← {topic.title}
        </button>
        <ul className="mt-2 space-y-2">
          {topic.subtopics.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => setSubId(s.id)}
                className="w-full rounded-2xl border bg-card p-4 text-left shadow-soft transition-all hover:border-violet-300"
              >
                <span className="font-bold">{s.title}</span>
                <span className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{s.core_count} core learning targets</span>
                  <span>Mastery: {masteryLabel(s.coverage.mastery)}</span>
                  <span>
                    Coverage: {s.coverage.practiced}/{s.coverage.total}
                  </span>
                </span>
                <ProgressBar value={s.coverage.mastery} className="mt-2" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setSubId(null)}
        className="text-sm font-semibold text-violet-700 hover:underline"
      >
        ← {sub.title}
      </button>
      <ul className="mt-2 space-y-2">
        {sub.concepts.map((c) => (
          <li key={c.id} className="rounded-2xl border bg-card p-4 shadow-soft">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => onOpen(c.id)}
                className="font-bold hover:underline"
              >
                {c.title}
              </button>
              <Badge tint="violet">{c.lo_type}</Badge>
              <Badge tint={statusTint(c.status)}>{c.status}</Badge>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <ProgressBar value={c.mastery} className="flex-1" />
              <span className="text-sm font-extrabold text-gradient">{masteryLabel(c.mastery)}</span>
              <PracticeButton onClick={() => onPractice(c.id)} disabled={busy} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Search({
  projectId,
  busy,
  onPractice,
  onOpen,
}: {
  projectId: string
  busy: boolean
  onPractice: (id: string) => void
  onOpen: (id: string) => void
}) {
  const [query, setQuery] = useState("")
  const [hits, setHits] = useState<Hit[] | null>(null)
  const [searching, setSearching] = useState(false)

  async function run() {
    const q = query.trim()
    if (q.length < 2) return
    setSearching(true)
    try {
      const res = await apiClient.get<{ hits: Hit[] }>(
        `/projects/${projectId}/knowledge/search?q=${encodeURIComponent(q)}`,
      )
      setHits(res.data.hits)
    } catch {
      setHits([])
    } finally {
      setSearching(false)
    }
  }

  return (
    <div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          void run()
        }}
      >
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search concepts… (min 2 characters)"
          aria-label="Search learning objects"
        />
        <Button type="submit" disabled={searching || query.trim().length < 2}>
          <SearchIcon className="h-4 w-4" /> Search
        </Button>
      </form>
      {searching && <LoadingState text="Searching…" />}
      {hits !== null && !searching && hits.length === 0 && (
        <p className="mt-3 text-sm text-muted-foreground">No matches — try a different term.</p>
      )}
      {hits !== null && hits.length > 0 && (
        <ul className="mt-3 space-y-2">
          {hits.map((hit) => (
            <li key={hit.id} className="rounded-2xl border bg-card p-4 shadow-soft">
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" onClick={() => onOpen(hit.id)} className="font-bold hover:underline">
                  {hit.title}
                </button>
                <Badge tint="violet">{hit.lo_type}</Badge>
                {hit.importance !== "CORE" && <Badge tint="muted">{hit.importance}</Badge>}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {hit.topic} → {hit.subtopic}
                {hit.page_start !== null && ` · page ${hit.page_start}`}
                {hit.mastery !== null && ` · mastery ${Math.round(hit.mastery)}%`}
              </p>
              {hit.practicable && (
                <div className="mt-2">
                  <PracticeButton onClick={() => onPractice(hit.id)} disabled={busy} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const MODES: { id: Mode; label: string; icon: React.ReactNode }[] = [
  { id: "recommended", label: "Recommended", icon: <Compass className="h-4 w-4" /> },
  { id: "browse", label: "Browse by Topic", icon: <FolderTree className="h-4 w-4" /> },
  { id: "search", label: "Search", icon: <SearchIcon className="h-4 w-4" /> },
]

export function QuizModes({
  projectId,
  busy,
  onPractice,
}: {
  projectId: string
  busy: boolean
  onPractice: (conceptId: string) => void
}) {
  const [mode, setMode] = useState<Mode>("recommended")
  const [detailId, setDetailId] = useState<string | null>(null)

  return (
    <div>
      <div role="tablist" aria-label="Quiz modes" className="flex gap-1 rounded-2xl border bg-card p-1 shadow-soft">
        {MODES.map((m) => (
          <button
            key={m.id}
            role="tab"
            aria-selected={mode === m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold transition-all",
              mode === m.id
                ? "bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-soft"
                : "text-muted-foreground hover:bg-muted",
            )}
          >
            {m.icon}
            <span className="hidden sm:inline">{m.label}</span>
            <span className="sm:hidden">{m.label.split(" ")[0]}</span>
          </button>
        ))}
      </div>
      <div className="mt-4">
        {mode === "recommended" && (
          <Recommended projectId={projectId} busy={busy} onPractice={onPractice} onOpen={setDetailId} />
        )}
        {mode === "browse" && (
          <Browse projectId={projectId} busy={busy} onPractice={onPractice} onOpen={setDetailId} />
        )}
        {mode === "search" && (
          <Search projectId={projectId} busy={busy} onPractice={onPractice} onOpen={setDetailId} />
        )}
      </div>
      {detailId && (
        <div className="mt-4">
          <ConceptDetail
            projectId={projectId}
            conceptId={detailId}
            onClose={() => setDetailId(null)}
            onPractice={(id) => {
              setDetailId(null)
              onPractice(id)
            }}
            onOpen={setDetailId}
          />
        </div>
      )}
    </div>
  )
}
