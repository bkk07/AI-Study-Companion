import { useEffect, useState } from "react"
import { Compass, FolderTree, Play, Search as SearchIcon, Sparkles, Wand2 } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, Button, EmptyState, Input, LoadingState, ProgressBar, Tag } from "@/components/ui"
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
      <Play size={14} /> Practice
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
  if (hero) {
    return (
      <div className="rounded-xl bg-indigo-600 p-5 text-white sm:p-6">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-200">
          <Sparkles size={14} /> Recommended for you
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onOpen(candidate.concept_id)}
            className="text-left text-xl font-semibold text-white hover:underline"
          >
            {candidate.name}
          </button>
          {candidate.lo_type && (
            <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium text-white">{candidate.lo_type}</span>
          )}
        </div>
        <p className="mt-2 text-sm text-indigo-100">{candidate.reasoning}</p>
        <div className="mt-4">
          <button
            type="button"
            onClick={() => onPractice(candidate.concept_id)}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
          >
            <Play size={14} /> Start Practice
          </button>
        </div>
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onOpen(candidate.concept_id)}
          className="text-left text-base font-semibold text-slate-900 hover:underline"
        >
          {candidate.name}
        </button>
        {candidate.lo_type && <Tag color="indigo">{candidate.lo_type}</Tag>}
        <Badge tint={candidate.fallback ? "muted" : statusTint(candidate.status)}>
          {candidate.fallback ? "Get started" : candidate.status}
        </Badge>
      </div>
      {!candidate.fallback && (
        <div className="mt-2 flex items-center gap-3">
          <ProgressBar value={candidate.mastery} className="flex-1" barClass="bg-indigo-500" />
          <span className="font-mono-data text-sm font-semibold text-slate-800">
            {masteryLabel(candidate.mastery)}
          </span>
        </div>
      )}
      <p className="mt-2 text-sm text-slate-500">{candidate.reasoning}</p>
      <div className="mt-3">
        <PracticeButton onClick={() => onPractice(candidate.concept_id)} disabled={busy} />
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
        icon={<Wand2 size={24} />}
        title="No practice targets yet"
        hint="Upload a PDF and recommendations unlock once it's processed."
      />
    )
  if (!data) return <LoadingState text="Finding what to practice…" />
  if (data.items.length === 0 && !data.fallback)
    return (
      <EmptyState
        icon={<Wand2 size={24} />}
        title="No practice targets yet"
        hint="Upload a PDF and recommendations unlock once it's processed."
      />
    )
  const [hero, ...rest] = data.items
  return (
    <div className="space-y-3">
      {hero && <CandidateCard candidate={hero} hero busy={busy} onPractice={onPractice} onOpen={onOpen} />}
      {data.fallback && (
        <CandidateCard candidate={data.fallback} busy={busy} onPractice={onPractice} onOpen={onOpen} />
      )}
      {rest.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Other recommendations
          </p>
          <div className="space-y-2">
            {rest.map((c) => (
              <CandidateCard key={c.concept_id} candidate={c} busy={busy} onPractice={onPractice} onOpen={onOpen} />
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
        icon={<FolderTree size={24} />}
        title="No topics yet"
        hint="Upload a PDF and browse unlocks once it's processed."
      />
    )
  if (!tree) return <LoadingState text="Loading topics…" />
  if (tree.length === 0)
    return (
      <EmptyState
        icon={<FolderTree size={24} />}
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
              className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left transition-all hover:border-slate-300 hover:shadow-sm"
            >
              <span className="text-sm font-semibold text-slate-900">{t.title}</span>
              <span className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                <span>{t.core_count} core learning targets</span>
                <span>Mastery: {masteryLabel(t.coverage.mastery)}</span>
                <span>
                  Coverage: {t.coverage.practiced}/{t.coverage.total}
                </span>
              </span>
              <ProgressBar value={t.coverage.mastery} className="mt-2" barClass="bg-indigo-500" />
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
          className="text-sm font-medium text-indigo-600 hover:underline"
        >
          ← {topic.title}
        </button>
        <ul className="mt-2 space-y-2">
          {topic.subtopics.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => setSubId(s.id)}
                className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left transition-all hover:border-slate-300 hover:shadow-sm"
              >
                <span className="text-sm font-semibold text-slate-900">{s.title}</span>
                <span className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                  <span>{s.core_count} core learning targets</span>
                  <span>Mastery: {masteryLabel(s.coverage.mastery)}</span>
                  <span>
                    Coverage: {s.coverage.practiced}/{s.coverage.total}
                  </span>
                </span>
                <ProgressBar value={s.coverage.mastery} className="mt-2" barClass="bg-indigo-500" />
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
        className="text-sm font-medium text-indigo-600 hover:underline"
      >
        ← {sub.title}
      </button>
      <ul className="mt-2 space-y-2">
        {sub.concepts.map((c) => (
          <li key={c.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => onOpen(c.id)}
                className="text-sm font-semibold text-slate-900 hover:underline"
              >
                {c.title}
              </button>
              <Tag color="indigo">{c.lo_type}</Tag>
              <Badge tint={statusTint(c.status)}>{c.status}</Badge>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <ProgressBar value={c.mastery} className="flex-1" barClass="bg-indigo-500" />
              <span className="font-mono-data text-sm font-semibold text-slate-800">{masteryLabel(c.mastery)}</span>
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
          <SearchIcon size={15} /> Search
        </Button>
      </form>
      {searching && <LoadingState text="Searching…" />}
      {hits !== null && !searching && hits.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">No matches — try a different term.</p>
      )}
      {hits !== null && hits.length > 0 && (
        <ul className="mt-3 space-y-2">
          {hits.map((hit) => (
            <li key={hit.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" onClick={() => onOpen(hit.id)} className="text-sm font-semibold text-slate-900 hover:underline">
                  {hit.title}
                </button>
                <Tag color="indigo">{hit.lo_type}</Tag>
                {hit.importance !== "CORE" && <Badge tint="muted">{hit.importance}</Badge>}
              </div>
              <p className="mt-1 text-xs text-slate-500">
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
  { id: "recommended", label: "Recommended", icon: <Compass size={16} /> },
  { id: "browse", label: "Browse by Topic", icon: <FolderTree size={16} /> },
  { id: "search", label: "Search", icon: <SearchIcon size={16} /> },
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
      <div role="tablist" aria-label="Quiz modes" className="flex gap-1 rounded-xl border border-slate-200 bg-white p-1">
        {MODES.map((m) => (
          <button
            key={m.id}
            role="tab"
            aria-selected={mode === m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all",
              mode === m.id
                ? "bg-indigo-600 text-white"
                : "text-slate-500 hover:bg-slate-50",
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
