import { useEffect, useState } from "react"
import { ChartColumn } from "lucide-react"
import apiClient from "@/lib/axios"
import { Badge, EmptyState, LoadingState, ProgressBar, SectionHeader, Tag } from "@/components/ui"
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
      <div className="rounded-xl border border-slate-200 bg-white">
        <EmptyState
          icon={<ChartColumn size={24} />}
          title="No progress yet"
          hint="Practice a quiz or explain a concept and your knowledge map fills in here."
        />
      </div>
    )
  if (!tree) return <LoadingState text="Loading progress…" />

  const topic = tree.topics.find((t) => t.id === topicId) ?? null
  const sub = topic?.subtopics.find((s) => s.id === subId) ?? null

  return (
    <div>
      <SectionHeader title="Progress Map" subtitle="Topic → Subtopic → Concept coverage" />
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Overall mastery</div>
        <p className="font-mono-data text-3xl font-bold text-slate-900">
          {masteryLabel(tree.overall.mastery)}
        </p>
        <ProgressBar value={tree.overall.mastery} className="mt-2" barClass="bg-indigo-500" />
        <p className="mt-1.5 text-xs text-slate-500">
          {tree.overall.practiced} of {tree.overall.total} core learning targets practiced
        </p>
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-6">
        {!topic && (
          <div className="space-y-3">
            {tree.topics.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setTopicId(t.id)
                  setSubId(null)
                }}
                className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left transition-all hover:border-slate-300 hover:shadow-sm"
              >
                <span className="text-sm font-semibold text-slate-900">{t.title}</span>
                <span className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-500">
                  <span>Mastery: {masteryLabel(t.coverage.mastery)}</span>
                  <span>Coverage: {t.coverage.practiced}/{t.coverage.total} practiced</span>
                </span>
                <ProgressBar value={t.coverage.mastery} className="mt-2" barClass="bg-indigo-500" />
              </button>
            ))}
          </div>
        )}
        {topic && !sub && (
          <div>
            <button
              type="button"
              onClick={() => setTopicId(null)}
              className="text-sm font-medium text-indigo-600 hover:underline"
            >
              ← {topic.title}
            </button>
            <div className="mt-2 space-y-2">
              {topic.subtopics.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSubId(s.id)}
                  className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left transition-all hover:border-slate-300"
                >
                  <span className="text-sm font-semibold text-slate-900">{s.title}</span>
                  <span className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-500">
                    <span>Mastery: {masteryLabel(s.coverage.mastery)}</span>
                    <span>Coverage: {s.coverage.practiced}/{s.coverage.total}</span>
                  </span>
                  <ProgressBar value={s.coverage.mastery} className="mt-2" barClass="bg-indigo-500" />
                </button>
              ))}
            </div>
          </div>
        )}
        {topic && sub && (
          <div>
            <button
              type="button"
              onClick={() => setSubId(null)}
              className="text-sm font-medium text-indigo-600 hover:underline"
            >
              ← {sub.title}
            </button>
            <div className="mt-2 space-y-2">
              {sub.concepts.map((c) => (
                <div key={c.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900">{c.title}</span>
                    <Tag color="indigo">{c.lo_type}</Tag>
                    <Badge tint={statusTint(c.status)}>{c.status}</Badge>
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <ProgressBar value={c.mastery} className="flex-1" barClass="bg-indigo-500" />
                    <span className="font-mono-data text-sm font-semibold text-slate-800">
                      {masteryLabel(c.mastery)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function ProgressMapCard({ projectId }: { projectId: string }) {
  return <ProgressMap projectId={projectId} />
}
