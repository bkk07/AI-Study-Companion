import { useEffect, useState } from "react"
import { ChartColumn, FolderTree } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, Card, EmptyState, LoadingState, ProgressBar } from "@/components/ui"
import { statusTint } from "@/features/quiz/ConceptDetail"

type Coverage = { mastery: number | null; practiced: number; total: number }

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
  coverage: Coverage
  concepts: Leaf[]
}

type TopicNode = {
  id: string
  title: string
  core_count: number
  coverage: Coverage
  subtopics: SubtopicNode[]
}

type Tree = { topics: TopicNode[]; overall: Coverage }

function masteryLabel(mastery: number | null): string {
  return mastery === null ? "Not started" : `${Math.round(mastery)}%`
}

function CoverageLine({ coverage }: { coverage: Coverage }) {
  return (
    <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
      <span>Mastery: {masteryLabel(coverage.mastery)}</span>
      <span>
        Coverage: {coverage.practiced}/{coverage.total} practiced
      </span>
    </span>
  )
}

export function ProgressMap({ projectId }: { projectId: string }) {
  const [tree, setTree] = useState<Tree | null>(null)
  const [failed, setFailed] = useState(false)
  const [topicId, setTopicId] = useState<string | null>(null)
  const [subId, setSubId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<Tree>(`/projects/${projectId}/knowledge/tree`)
      .then((res) => {
        if (!cancelled) setTree(res.data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  if (failed || (tree && tree.overall.total === 0))
    return (
      <EmptyState
        icon={<ChartColumn className="h-6 w-6" />}
        title="No progress yet"
        hint="Practice a quiz or explain a concept and your knowledge map fills in here."
      />
    )
  if (!tree) return <LoadingState text="Loading progress…" />

  const topic = tree.topics.find((t) => t.id === topicId) ?? null
  const sub = topic?.subtopics.find((s) => s.id === subId) ?? null

  return (
    <div>
      <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 p-5 text-white shadow-soft sm:p-6">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-white/80">
          <FolderTree className="h-4 w-4" /> Overall mastery
        </p>
        <p className="mt-1 text-3xl font-extrabold tracking-tight">
          {masteryLabel(tree.overall.mastery)}
        </p>
        <ProgressBar value={tree.overall.mastery} className="mt-2 bg-white/25" />
        <p className="mt-1.5 text-xs text-white/85">
          {tree.overall.practiced} of {tree.overall.total} core learning targets practiced
        </p>
      </div>

      <div className="mt-3">
        {!topic && (
          <ul className="space-y-2">
            {tree.topics.map((t) => (
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
                  <CoverageLine coverage={t.coverage} />
                  <ProgressBar value={t.coverage.mastery} className="mt-2" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {topic && !sub && (
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
                    <CoverageLine coverage={s.coverage} />
                    <ProgressBar value={s.coverage.mastery} className="mt-2" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {topic && sub && (
          <div>
            <button
              type="button"
              onClick={() => setSubId(null)}
              className="text-sm font-semibold text-violet-700 hover:underline"
            >
              ← {sub.title}
            </button>
            <p className="mt-2">
              <CoverageLine coverage={sub.coverage} />
            </p>
            <ul className="mt-2 space-y-2">
              {sub.concepts.map((c) => (
                <li key={c.id} className="rounded-2xl border bg-card p-4 shadow-soft">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold">{c.title}</span>
                    <Badge tint="violet">{c.lo_type}</Badge>
                    <Badge tint={statusTint(c.status)}>{c.status}</Badge>
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <ProgressBar value={c.mastery} className="flex-1" />
                    <span className="text-sm font-extrabold text-gradient">
                      {masteryLabel(c.mastery)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

export function ProgressMapCard({ projectId }: { projectId: string }) {
  return (
    <Card className="p-5 sm:p-6">
      <h3 className="font-bold">Knowledge map</h3>
      <div className="mt-3">
        <ProgressMap projectId={projectId} />
      </div>
    </Card>
  )
}
