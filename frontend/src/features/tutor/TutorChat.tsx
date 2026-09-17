import React, { useEffect, useRef, useState } from "react"
import {
  BookOpen,
  BookOpenCheck,
  Brain,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileText,
  History,
  Lightbulb,
  Pin,
  Plus,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import "katex/dist/katex.min.css"
import type { DirectSession } from "@/features/quiz/QuizTaker"
import type { Card as FlashCard } from "@/features/flashcards/Flashcards"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { cn } from "@/lib/utils"

type Citation = {
  chunk_id: string
  material_id: string
  page_number: number | null
  source_name: string | null
  chunk_index: number
  excerpt: string | null
}

type Message =
  | { kind: "user"; text: string; time: string }
  | { kind: "assistant"; answer: string; supported: boolean; citations: Citation[]; followUps: string[]; time: string }
  | { kind: "failure"; text: string; question: string }

type Conversation = {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

type StoredMessage = {
  id: string
  role: string
  content: string
  supported: boolean | null
  citations: Citation[]
  follow_ups: string[]
  created_at: string
}

const WELCOME =
  "Hello! I'm your AI tutor for this project. I answer only from your uploaded study material, with **document and page citations** for everything I explain.\n\nTry asking me to *define a concept*, *explain how something works*, or *compare two ideas*."

function fmtTime(iso: string): string {
  const d = new Date(iso)
  return isNaN(d.getTime()) ? now() : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return isNaN(d.getTime()) ? "" : d.toLocaleDateString([], { month: "short", day: "numeric" })
}

function failureText(status?: number, detail?: string): string {
  if (status === 429) return "Slow down — too many tutor requests. Wait a moment and retry."
  if (status === 502) return "Tutor AI provider unavailable — no answer was generated. Retry when ready."
  if (status === 404) return "Project not found for this tutor session."
  return detail ?? "Failed to reach the tutor — no answer was generated."
}

function now(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

const THINKING_STEPS = [
  "Searching your project knowledge…",
  "Finding relevant material…",
  "Preparing explanation…",
]

/** Short follow-ups inherit the previous question's context ("give an example" → of what?). */
const FOLLOWUP_PREFIX =
  /^(give (me )?(an? )?example|explain simpl|explain deep|explain more|tell me more|compare|contrast|summar|why |how does (it|this|that) work|another example)/i

function expandFollowUp(draft: string, lastQuestion: string | null): string {
  const q = draft.trim()
  if (lastQuestion && FOLLOWUP_PREFIX.test(q) && q.toLowerCase() !== lastQuestion.toLowerCase()) {
    return `${q} — in the context of: "${lastQuestion}"`
  }
  return q
}

/* ---------- Markdown answer rendering ---------- */

function calloutKind(title: string): "simple" | "example" | "takeaway" | null {
  const t = title.toLowerCase()
  if (t.includes("simple terms") || t.includes("mental model")) return "simple"
  if (t.includes("example")) return "example"
  if (t.includes("takeaway") || t.includes("key difference") || t.includes("key point")) return "takeaway"
  return null
}

const CALLOUT_STYLES: Record<string, { box: string; icon: React.ReactNode; title: string }> = {
  simple: { box: "border-sky-200 bg-sky-50", icon: <Brain size={15} className="text-sky-600" />, title: "text-sky-800" },
  example: { box: "border-amber-200 bg-amber-50", icon: <Lightbulb size={15} className="text-amber-600" />, title: "text-amber-800" },
  takeaway: { box: "border-green-200 bg-green-50", icon: <Pin size={15} className="text-green-600" />, title: "text-green-800" },
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable — no-op */
    }
  }
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-700/60 px-3 py-1.5">
        <span className="font-mono-data text-[11px] text-slate-400">{language || "code"}</span>
        <button
          type="button"
          onClick={() => void copy()}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-slate-300 transition-colors hover:bg-slate-700 hover:text-white"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono-data text-[13px] leading-relaxed text-slate-100">
        <code>{code}</code>
      </pre>
    </div>
  )
}

/** Strip [n] citation markers (outside fenced code blocks) — all citation
 * information lives in the Sources panel, never inside the conversation. */
function stripCitations(source: string, valid: Set<number>): string {
  return source
    .split(/(```[\s\S]*?```)/g)
    .map((seg, i) => {
      if (i % 2 === 1) return seg // fenced block — untouched
      return seg.replace(/\[(\d+)\]/g, (m, n) => (valid.has(parseInt(n, 10)) ? "" : m))
    })
    .join("")
}

const mdComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-lg font-bold leading-snug text-slate-900">{children}</h3>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h4 className="text-[15px] font-bold text-slate-900">{children}</h4>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => {
    const title = React.Children.toArray(children).join("").toString()
    const kind = calloutKind(title)
    if (kind) {
      const s = CALLOUT_STYLES[kind]
      return (
        <div className={cn("rounded-xl border px-4 py-3", s.box)}>
          <p className={cn("flex items-center gap-1.5 text-sm font-bold", s.title)}>
            {s.icon} {title}
          </p>
        </div>
      )
    }
    return <h4 className="text-sm font-bold text-slate-900">{children}</h4>
  },
  h4: ({ children }: { children?: React.ReactNode }) => (
    <h5 className="text-sm font-bold text-slate-800">{children}</h5>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="text-sm leading-relaxed text-slate-700">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-slate-700">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-slate-700">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => <li className="pl-0.5">{children}</li>,
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => <thead className="bg-slate-50">{children}</thead>,
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border-b border-slate-200 px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
      {children}
    </th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border-b border-slate-100 px-3 py-2 align-top text-sm text-slate-700">{children}</td>
  ),
  code: ({ className, children }: { className?: string; children?: React.ReactNode }) => {
    const text = React.Children.toArray(children).join("").toString()
    if (text.includes("\n")) return <code className={className}>{children}</code>
    return (
      <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono-data text-[13px] text-slate-800">
        {children}
      </code>
    )
  },
  pre: ({ children }: { children?: React.ReactNode }) => {
    let language = ""
    let code = ""
    React.Children.forEach(children, (child) => {
      if (React.isValidElement<{ className?: string; children?: React.ReactNode }>(child)) {
        const cls = child.props.className ?? ""
        const match = cls.match(/language-(\w+)/)
        if (match) language = match[1]
        code = React.Children.toArray(child.props.children).join("").toString()
      }
    })
    if (!code) return <pre>{children}</pre>
    return <CodeBlock language={language} code={code.replace(/\n$/, "")} />
  },
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a href={href} className="font-medium text-indigo-600 hover:underline">
      {children}
    </a>
  ),
}

/** Render markdown answer text (citation-free — see Sources panel). */
function AnswerBody({
  answer,
  citations,
}: {
  answer: string
  citations: Citation[]
}) {
  const valid = React.useMemo(
    () => new Set(citations.map((c) => c.chunk_index)),
    [citations],
  )
  const source = React.useMemo(() => stripCitations(answer, valid), [answer, valid])
  return (
    <div className="tutor-math space-y-3">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={mdComponents}
      >
        {source}
      </ReactMarkdown>
    </div>
  )
}

function groupConvos(convos: Conversation[]): { label: string; items: Conversation[] }[] {
  const startOf = new Date()
  startOf.setHours(0, 0, 0, 0)
  const yesterday = new Date(startOf)
  yesterday.setDate(startOf.getDate() - 1)
  const groups: { label: string; items: Conversation[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Older", items: [] },
  ]
  for (const c of convos) {
    const d = new Date(c.updated_at)
    if (isNaN(d.getTime()) || d < yesterday) groups[2].items.push(c)
    else if (d < startOf) groups[1].items.push(c)
    else groups[0].items.push(c)
  }
  return groups.filter((g) => g.items.length > 0)
}

function HistoryPanel({
  convos,
  activeId,
  loading,
  onOpen,
  onNew,
  onDelete,
}: {
  convos: Conversation[] | null
  activeId: string | null
  loading: boolean
  onOpen: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}) {
  const [q, setQ] = useState("")
  const needle = q.trim().toLowerCase()
  const filtered = (convos ?? []).filter((c) => !needle || c.title.toLowerCase().includes(needle))
  const groups = groupConvos(filtered)
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-2 p-2">
        <button
          type="button"
          onClick={onNew}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus size={14} /> New Chat
        </button>
      </div>
      <div className="relative px-2 pb-2">
        <Search size={13} className="pointer-events-none absolute left-4 top-1/2 -translate-y-[calc(50%+4px)] text-slate-400" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search conversations"
          aria-label="Search conversations"
          className="w-full rounded-lg border border-slate-200 py-2 pl-8 pr-2 text-xs text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2" role="list" aria-label="Conversation history">
        {loading || convos === null ? (
          <p className="px-2 py-6 text-center text-xs text-slate-400">Loading chats…</p>
        ) : filtered.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-slate-400">
            {needle ? `No matches for “${q.trim()}”.` : "No previous chats yet — ask something to start one."}
          </p>
        ) : (
          groups.map((g) => (
            <div key={g.label} className="mb-1">
              <p className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{g.label}</p>
              {g.items.map((c) => (
                <div
                  key={c.id}
                  role="listitem"
                  className={cn(
                    "group flex items-center gap-1 rounded-lg px-2 py-2 transition-colors hover:bg-slate-50",
                    c.id === activeId && "bg-indigo-50 hover:bg-indigo-50",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => onOpen(c.id)}
                    aria-current={c.id === activeId}
                    className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
                  >
                    <span className={cn("block truncate text-[13px]", c.id === activeId ? "font-semibold text-indigo-900" : "font-medium text-slate-700")}>
                      {c.title}
                    </span>
                    <span className="block text-[11px] text-slate-400">
                      {fmtDate(c.updated_at)}
                      {c.message_count > 0 ? ` · ${Math.ceil(c.message_count / 2)} exchange${c.message_count > 2 ? "s" : ""}` : ""}
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete chat ${c.title}`}
                    onClick={() => onDelete(c.id)}
                    className="rounded p-1.5 text-slate-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

/* ---------- Main chat ---------- */

export function TutorChat({
  projectId,
  onQuizMe,
  onFlashcards,
  onQuizReady,
  onPracticeReady,
  onFlashcardsReady,
}: {
  projectId: string
  onQuizMe?: () => void
  onFlashcards?: () => void
  onQuizReady?: (s: DirectSession) => void
  onPracticeReady?: (p: { conceptIds: string[]; mcqCount: number; oeCount: number }) => void
  onFlashcardsReady?: (d: { cards: FlashCard[] }) => void
}) {
  const [messages, setMessages] = useState<Message[]>([
    { kind: "assistant", answer: WELCOME, supported: true, citations: [], followUps: [], time: now() },
  ])
  const [draft, setDraft] = useState("")
  const [pending, setPending] = useState(false)
  const [thinkStep, setThinkStep] = useState(0)
  const [activeSource, setActiveSource] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [convos, setConvos] = useState<Conversation[] | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [railCollapsed, setRailCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [sourcesOpen, setSourcesOpen] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const thinkTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => () => {
    if (thinkTimer.current) clearInterval(thinkTimer.current)
  }, [])

  const lastUserQuestion = [...messages].reverse().find((m) => m.kind === "user")?.text ?? null
  const lastUserTexts = [...messages]
    .filter((m): m is Extract<Message, { kind: "user" }> => m.kind === "user")
    .slice(-5)
    .map((m) => m.text)

  type PlanKind = "quiz" | "practice" | "flashcards"
  type PlanFlow =
    | { kind: PlanKind; step: "planning" }
    | { kind: PlanKind; step: "confirm"; label: string; conceptIds: string[] }
    | { kind: "quiz" | "flashcards"; step: "count"; label: string; conceptIds: string[]; count: number; busy: boolean; error: string | null }
    | { kind: "practice"; step: "count"; label: string; conceptIds: string[]; mcq: number; oe: number; busy: boolean; error: string | null }
  const [planFlow, setPlanFlow] = useState<PlanFlow | null>(null)

  const pushNote = (text: string) =>
    setMessages((m) => [...m, { kind: "assistant", answer: text, supported: true, citations: [], followUps: [], time: now() }])

  const PLAN_NOUNS: Record<PlanKind, { item: string; confirm: string; none: string }> = {
    quiz: { item: "quiz", confirm: "Are you sure you want a quiz on", none: "then tap **Quiz me**" },
    practice: { item: "practice session", confirm: "Are you sure you want to practice", none: "then tap **Practice**" },
    flashcards: { item: "flashcards", confirm: "Are you sure you want flashcards on", none: "then tap **Flashcards**" },
  }

  async function startPlan(kind: PlanKind) {
    if (pending || planFlow) return
    if (lastUserTexts.length === 0) {
      pushNote(`Chat with me first — ask me anything from your materials, ${PLAN_NOUNS[kind].none} and I'll build ${kind === "quiz" ? "you a quiz" : kind} on what we discussed.`)
      return
    }
    setPlanFlow({ kind, step: "planning" })
    try {
      const res = await apiClient.post<{ label: string; concept_ids: string[] }>(
        `/projects/${projectId}/tutor/quiz-plan`,
        { questions: lastUserTexts },
      )
      if (!res.data.concept_ids || res.data.concept_ids.length === 0) {
        setPlanFlow(null)
        pushNote("I couldn't pin down specific topics from our recent chat. Ask me about a topic first, then try again.")
        return
      }
      setPlanFlow({ kind, step: "confirm", label: res.data.label || "these topics", conceptIds: res.data.concept_ids })
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setPlanFlow(null)
      pushNote(status === 429 ? "Slow down — too many AI requests. Wait a moment and retry." : (detail ?? "Couldn't figure out the topics — try again."))
    }
  }

  function rateErr(status?: number, detail?: string, fallback = "Generation failed — nothing was lost."): string {
    if (status === 429) return "Slow down — too many AI requests. Wait a moment and retry."
    if (status === 422) return detail ?? "These topics can't be used yet."
    return detail ?? fallback
  }

  async function generatePlannedQuiz() {
    if (planFlow?.step !== "count" || planFlow.kind !== "quiz" || planFlow.busy) return
    setPlanFlow({ ...planFlow, busy: true, error: null })
    try {
      const gen = await apiClient.post<{ quiz_id: string }>(`/projects/${projectId}/quizzes/generate`, {
        scope: "practice",
        concept_ids: planFlow.conceptIds,
        num_questions: planFlow.count,
        mode: "practice",
        difficulty: null,
      })
      const start = await apiClient.post<{ attempt_id: string; questions: DirectSession["questions"] }>(
        `/projects/${projectId}/quizzes/${gen.data.quiz_id}/attempts`,
      )
      const flow = planFlow
      setPlanFlow(null)
      if (onQuizReady) {
        onQuizReady({ attemptId: start.data.attempt_id, questions: start.data.questions })
      } else {
        pushNote(`Your quiz on **${flow.label}** is ready with ${start.data.questions.length} questions.`)
        onQuizMe?.()
      }
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setPlanFlow({ ...planFlow, busy: false, error: rateErr(status, detail) })
    }
  }

  async function generatePlannedPractice() {
    if (planFlow?.step !== "count" || planFlow.kind !== "practice" || planFlow.busy) return
    if (planFlow.mcq + planFlow.oe < 1) {
      setPlanFlow({ ...planFlow, error: "Request at least one question to start." })
      return
    }
    const flow = planFlow
    setPlanFlow(null)
    onPracticeReady?.({ conceptIds: flow.conceptIds, mcqCount: flow.mcq, oeCount: flow.oe })
  }

  async function generatePlannedFlashcards() {
    if (planFlow?.step !== "count" || planFlow.kind !== "flashcards" || planFlow.busy) return
    setPlanFlow({ ...planFlow, busy: true, error: null })
    try {
      await apiClient.post(`/projects/${projectId}/flashcards/decks`, { concept_ids: planFlow.conceptIds })
      const params = new URLSearchParams()
      for (const id of planFlow.conceptIds) params.append("concept_ids", id)
      params.append("limit", "100")
      const res = await apiClient.get<{ cards: FlashCard[] }>(`/projects/${projectId}/flashcards?${params.toString()}`)
      const cards = res.data.cards.slice(0, planFlow.count)
      if (cards.length === 0) throw new Error("empty")
      const flow = planFlow
      setPlanFlow(null)
      if (onFlashcardsReady) {
        onFlashcardsReady({ cards })
      } else {
        pushNote(`Built ${cards.length} flashcards on **${flow.label}**.`)
        onFlashcards?.()
      }
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      const msg = e instanceof Error && e.message === "empty"
        ? "No flashcards could be built for these topics yet."
        : rateErr(status, detail)
      setPlanFlow({ ...planFlow, busy: false, error: msg })
    }
  }

  const refreshList = async () => {
    try {
      const res = await apiClient.get<Conversation[]>(`/projects/${projectId}/tutor/conversations`)
      setConvos(res.data)
    } catch {
      setConvos([])
    }
  }

  const openConversation = async (id: string) => {
    setMobileNavOpen(false)
    setHistoryLoading(true)
    try {
      const res = await apiClient.get<{ id: string; title: string; messages: StoredMessage[] }>(
        `/projects/${projectId}/tutor/conversations/${id}`,
      )
      setActiveId(res.data.id)
      const loaded: Message[] = res.data.messages.map((m) =>
        m.role === "user"
          ? { kind: "user" as const, text: m.content, time: fmtTime(m.created_at) }
          : {
              kind: "assistant" as const,
              answer: m.content,
              supported: m.supported ?? true,
              citations: m.citations ?? [],
              followUps: m.follow_ups ?? [],
              time: fmtTime(m.created_at),
            },
      )
      setMessages(
        loaded.length > 0
          ? loaded
          : [{ kind: "assistant", answer: WELCOME, supported: true, citations: [], followUps: [], time: now() }],
      )
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    } catch {
      /* keep current view on failure */
    } finally {
      setHistoryLoading(false)
    }
  }

  const newChat = () => {
    setMobileNavOpen(false)
    setActiveId(null)
    setMessages([{ kind: "assistant", answer: WELCOME, supported: true, citations: [], followUps: [], time: now() }])
    void refreshList()
  }

  const deleteChat = async (id: string) => {
    try {
      await apiClient.delete(`/projects/${projectId}/tutor/conversations/${id}`)
    } catch {
      /* missing is fine */
    }
    if (id === activeId) {
      setActiveId(null)
      setMessages([{ kind: "assistant", answer: WELCOME, supported: true, citations: [], followUps: [], time: now() }])
    }
    void refreshList()
  }

  // Load history on open: most recent chat restores, otherwise fresh welcome.
  useEffect(() => {
    let cancelled = false
    setConvos(null)
    setActiveId(null)
    setMobileNavOpen(false)
    setMessages([{ kind: "assistant", answer: WELCOME, supported: true, citations: [], followUps: [], time: now() }])
    apiClient
      .get<Conversation[]>(`/projects/${projectId}/tutor/conversations`)
      .then((res) => {
        if (cancelled) return
        setConvos(res.data)
        if (res.data.length > 0) void openConversation(res.data[0].id)
      })
      .catch(() => {
        if (!cancelled) setConvos([])
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function ask(rawQuestion: string) {
    const expanded = expandFollowUp(rawQuestion, lastUserQuestion)
    const q = expanded.trim()
    if (!q || pending) return
    setPending(true)
    setDraft("")
    setThinkStep(0)
    thinkTimer.current = setInterval(() => setThinkStep((s) => Math.min(s + 1, THINKING_STEPS.length - 1)), 1400)
    setMessages((m) => [...m, { kind: "user", text: rawQuestion.trim(), time: now() }])
    try {
      let cid = activeId
      if (!cid) {
        const created = await apiClient.post<Conversation>(`/projects/${projectId}/tutor/conversations`, {})
        cid = created.data.id
        setActiveId(cid)
      }
      const res = await apiClient.post<{
        answer: string
        supported: boolean
        citations: Citation[]
        follow_ups: string[]
      }>(`/projects/${projectId}/tutor/conversations/${cid}/messages`, { question: q })
      setMessages((m) => [
        ...m,
        {
          kind: "assistant",
          answer: res.data.answer,
          supported: res.data.supported,
          citations: res.data.citations,
          followUps: res.data.follow_ups ?? [],
          time: now(),
        },
      ])
      void refreshList()
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setMessages((m) => [...m, { kind: "failure", text: failureText(status, detail), question: q }])
    } finally {
      if (thinkTimer.current) clearInterval(thinkTimer.current)
      thinkTimer.current = null
      setPending(false)
    }
  }

  const copyAnswer = async (idx: number, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(idx)
      setTimeout(() => setCopiedId(null), 1500)
    } catch {
      /* clipboard unavailable — no-op */
    }
  }

  const regenerate = (idx: number) => {
    if (pending) return
    for (let k = idx - 1; k >= 0; k--) {
      const prev = messages[k]
      if (prev?.kind === "user") {
        void ask(prev.text)
        return
      }
    }
  }

  const studyActions = [
    { label: "Quiz me", run: () => void startPlan("quiz") },
    { label: "Practice", run: () => void startPlan("practice") },
    { label: "Flashcards", run: () => void startPlan("flashcards") },
    { label: "Explain simply", run: () => lastUserQuestion && void ask(`Explain simply: ${lastUserQuestion}`) },
    { label: "Explain deeply", run: () => lastUserQuestion && void ask(`Explain in depth: ${lastUserQuestion}`) },
    { label: "Give example", run: () => lastUserQuestion && void ask(`Give an example — in the context of: "${lastUserQuestion}"`) },
    { label: "Summarize", run: () => lastUserQuestion && void ask(`Summarize — in the context of: "${lastUserQuestion}"`) },
  ]

  const lastAssistant = [...messages].reverse().find((m) => m.kind === "assistant") as
    | { kind: "assistant"; citations: Citation[] }
    | undefined
  const sources = lastAssistant?.citations ?? []
  const activeTitle = convos?.find((c) => c.id === activeId)?.title ?? "New chat"

  return (
    <div className="flex h-[calc(100dvh-230px)] min-h-[520px] flex-col sm:h-[calc(100dvh-57px)] sm:min-h-[560px]">
      {/* Mobile history access */}
      <div className="mb-2 flex items-center gap-2 md:hidden">
        <button
          type="button"
          onClick={() => setMobileNavOpen(true)}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
        >
          <History size={14} className="shrink-0 text-slate-400" />
          <span className="truncate">{historyLoading ? "Loading chat…" : activeTitle}</span>
        </button>
        <button
          type="button"
          onClick={newChat}
          aria-label="New chat"
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
        >
          <Plus size={14} />
        </button>
      </div>

      <div className="flex min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200 bg-white sm:rounded-none sm:border-0">
        {/* AREA 2 — Tutor chat history rail (desktop) */}
        <div
          className={cn(
            "hidden shrink-0 flex-col overflow-hidden border-r border-slate-200 bg-white transition-all duration-200 md:flex",
            railCollapsed ? "w-12 items-center py-2" : "w-64",
          )}
        >
          {railCollapsed ? (
            <div className="flex flex-col items-center gap-1">
              <button
                type="button"
                onClick={() => setRailCollapsed(false)}
                aria-label="Expand chat history"
                title="Expand chat history"
                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
              >
                <ChevronRight size={16} />
              </button>
              <button
                type="button"
                onClick={newChat}
                aria-label="New chat"
                title="New chat"
                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
              >
                <Plus size={16} />
              </button>
              <button
                type="button"
                onClick={() => setRailCollapsed(false)}
                aria-label="Open chat history"
                title="Chat history"
                className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              >
                <History size={16} />
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between px-3 pb-1 pt-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Chats</span>
                <button
                  type="button"
                  onClick={() => setRailCollapsed(true)}
                  aria-label="Collapse chat history"
                  title="Collapse"
                  className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                >
                  <ChevronLeft size={15} />
                </button>
              </div>
              <HistoryPanel
                convos={convos}
                activeId={activeId}
                loading={historyLoading}
                onOpen={(id) => void openConversation(id)}
                onNew={newChat}
                onDelete={(id) => void deleteChat(id)}
              />
            </>
          )}
        </div>

        {/* Mobile history overlay */}
        {mobileNavOpen && (
          <div className="fixed inset-0 z-50 md:hidden">
            <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMobileNavOpen(false)} aria-hidden />
            <div className="absolute bottom-0 left-0 top-0 flex w-72 flex-col rounded-r-2xl bg-white shadow-2xl">
              <div className="flex items-center justify-between px-3 pb-1 pt-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Chats</span>
                <button
                  type="button"
                  onClick={() => setMobileNavOpen(false)}
                  aria-label="Close chat history"
                  className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
                >
                  <X size={15} />
                </button>
              </div>
              <HistoryPanel
                convos={convos}
                activeId={activeId}
                loading={historyLoading}
                onOpen={(id) => {
                  setMobileNavOpen(false)
                  void openConversation(id)
                }}
                onNew={() => {
                  setMobileNavOpen(false)
                  newChat()
                }}
                onDelete={(id) => void deleteChat(id)}
              />
            </div>
          </div>
        )}

        {/* AREA 3 — Main tutor workspace */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <div className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6 sm:px-6" aria-live="polite">
          {messages.map((msg, i) =>
            msg.kind === "user" ? (
              <div key={i} className="flex flex-row-reverse gap-4">
                <div className="ml-auto max-w-lg">
                  <div className="rounded-2xl rounded-br-md bg-indigo-600 px-4 py-3 text-sm text-white">
                    <p className="leading-relaxed">{msg.text}</p>
                  </div>
                  <div className="mt-1 px-1 text-xs text-slate-400">{msg.time}</div>
                </div>
              </div>
            ) : msg.kind === "assistant" ? (
              <div key={i} className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600">
                  <BookOpen size={14} className="text-white" />
                </div>
                <div className="min-w-0 max-w-2xl flex-1">
                  <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                    AI Tutor
                  </p>
                  {msg.supported ? (
                    <div>
                      <AnswerBody answer={msg.answer} citations={msg.citations} />

                      <p className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                        <span className="inline-flex items-center gap-1.5 font-medium text-green-700">
                          <span className="h-2 w-2 rounded-full bg-green-500" aria-hidden />
                          Grounded in your project knowledge
                        </span>
                        {msg.citations.length > 0 && (
                          <span className="text-slate-400">
                            · {msg.citations.length} relevant source{msg.citations.length === 1 ? "" : "s"}
                          </span>
                        )}
                      </p>

                      {msg.followUps.length > 0 && (
                        <div className="mt-4">
                          <p className="mb-2 text-xs font-semibold text-slate-500">You might also ask:</p>
                          <div className="flex flex-col items-stretch gap-2">
                            {msg.followUps.map((f, k) => (
                              <button
                                key={k}
                                type="button"
                                disabled={pending}
                                onClick={() => void ask(f)}
                                className="rounded-xl border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-left text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-50"
                              >
                                {f}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-2.5 flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => void copyAnswer(i, msg.answer)}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                        >
                          {copiedId === i ? <Check size={12} /> : <Copy size={12} />}
                          {copiedId === i ? "Copied" : "Copy"}
                        </button>
                        <button
                          type="button"
                          onClick={() => regenerate(i)}
                          disabled={pending}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
                        >
                          <RefreshCw size={12} /> Regenerate
                        </button>
                        <button
                          type="button"
                          onClick={() => inputRef.current?.focus()}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                        >
                          Ask follow-up
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                      <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                        <BookOpenCheck size={15} className="text-indigo-500" />
                        Not enough information in your project knowledge
                      </p>
                      <p className="mt-1.5 whitespace-pre-line text-sm leading-relaxed text-slate-600">{msg.answer}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        Try asking about a topic from your uploaded materials — every answer cites its sources.
                      </p>
                    </div>
                  )}
                  <div className="mt-1 px-1 text-xs text-slate-400">{msg.time}</div>
                </div>
              </div>
            ) : (
              <div key={i} className="flex gap-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100">
                  <Sparkles size={14} className="text-red-500" />
                </div>
                <div className="max-w-lg rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm">
                  <p className="font-medium text-red-700">{msg.text}</p>
                  <p className="mt-0.5 text-xs text-red-500">I couldn&apos;t generate an answer right now.</p>
                  <button
                    type="button"
                    onClick={() => void ask(msg.question)}
                    disabled={pending}
                    className="mt-1 text-sm font-medium text-indigo-600 hover:underline disabled:opacity-50"
                  >
                    Try again
                  </button>
                </div>
              </div>
            ),
          )}
          {planFlow && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600">
                <BookOpen size={14} className="text-white" />
              </div>
              <div className="max-w-lg flex-1 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
                {planFlow.step === "planning" && (
                  <p className="flex items-center gap-2 text-sm text-slate-600">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                    Finding topics from our recent chat…
                  </p>
                )}
                {planFlow.step === "confirm" && (
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      {PLAN_NOUNS[planFlow.kind].confirm} <strong>{planFlow.label}</strong>?
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          planFlow.kind === "practice"
                            ? setPlanFlow({ kind: "practice", step: "count", label: planFlow.label, conceptIds: planFlow.conceptIds, mcq: 5, oe: 2, busy: false, error: null })
                            : setPlanFlow({ kind: planFlow.kind, step: "count", label: planFlow.label, conceptIds: planFlow.conceptIds, count: planFlow.kind === "quiz" ? 5 : 10, busy: false, error: null })
                        }
                        className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700"
                      >
                        Yes
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setPlanFlow(null)
                          pushNote("No problem — say the word whenever you want to revise.")
                        }}
                        className="rounded-lg border border-slate-200 bg-white px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
                      >
                        No
                      </button>
                    </div>
                  </div>
                )}
                {planFlow.step === "count" && planFlow.kind === "quiz" && (
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      How many questions on <strong>{planFlow.label}</strong>?
                    </p>
                    <div className="mt-3 flex items-center gap-3">
                      <button
                        type="button"
                        aria-label="Fewer questions"
                        disabled={planFlow.busy || planFlow.count <= 1}
                        onClick={() => setPlanFlow({ ...planFlow, count: Math.max(1, planFlow.count - 1) })}
                        className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                      >
                        −
                      </button>
                      <span aria-live="polite" className="font-mono-data min-w-8 text-center text-xl font-bold text-slate-900">
                        {planFlow.count}
                      </span>
                      <button
                        type="button"
                        aria-label="More questions"
                        disabled={planFlow.busy || planFlow.count >= 20}
                        onClick={() => setPlanFlow({ ...planFlow, count: Math.min(20, planFlow.count + 1) })}
                        className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                      >
                        +
                      </button>
                      <button
                        type="button"
                        onClick={() => void generatePlannedQuiz()}
                        disabled={planFlow.busy}
                        className="ml-1 flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {planFlow.busy && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
                        {planFlow.busy ? "Starting…" : "Start quiz"}
                      </button>
                    </div>
                    {planFlow.error && <p className="mt-2 text-xs text-red-600">{planFlow.error}</p>}
                  </div>
                )}
                {planFlow.step === "count" && planFlow.kind === "practice" && (
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      How many questions for <strong>{planFlow.label}</strong>?
                    </p>
                    <div className="mt-3 space-y-2.5">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-600">MCQs</span>
                        <span className="flex items-center gap-2.5">
                          <button
                            type="button"
                            aria-label="Fewer MCQs"
                            disabled={planFlow.busy || planFlow.mcq <= 0}
                            onClick={() => setPlanFlow({ ...planFlow, mcq: Math.max(0, planFlow.mcq - 1) })}
                            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                          >
                            −
                          </button>
                          <span aria-live="polite" className="font-mono-data min-w-8 text-center text-xl font-bold text-slate-900">
                            {planFlow.mcq}
                          </span>
                          <button
                            type="button"
                            aria-label="More MCQs"
                            disabled={planFlow.busy || planFlow.mcq >= 20}
                            onClick={() => setPlanFlow({ ...planFlow, mcq: Math.min(20, planFlow.mcq + 1) })}
                            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                          >
                            +
                          </button>
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-600">Open-ended</span>
                        <span className="flex items-center gap-2.5">
                          <button
                            type="button"
                            aria-label="Fewer open-ended"
                            disabled={planFlow.busy || planFlow.oe <= 0}
                            onClick={() => setPlanFlow({ ...planFlow, oe: Math.max(0, planFlow.oe - 1) })}
                            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                          >
                            −
                          </button>
                          <span aria-live="polite" className="font-mono-data min-w-8 text-center text-xl font-bold text-slate-900">
                            {planFlow.oe}
                          </span>
                          <button
                            type="button"
                            aria-label="More open-ended"
                            disabled={planFlow.busy || planFlow.oe >= 10}
                            onClick={() => setPlanFlow({ ...planFlow, oe: Math.min(10, planFlow.oe + 1) })}
                            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                          >
                            +
                          </button>
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => void generatePlannedPractice()}
                        disabled={planFlow.busy}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {planFlow.busy && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
                        {planFlow.busy ? "Starting…" : "Start practice"}
                      </button>
                    </div>
                    {planFlow.error && <p className="mt-2 text-xs text-red-600">{planFlow.error}</p>}
                  </div>
                )}
                {planFlow.step === "count" && planFlow.kind === "flashcards" && (
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      How many flashcards on <strong>{planFlow.label}</strong>?
                    </p>
                    <div className="mt-3 flex items-center gap-3">
                      <button
                        type="button"
                        aria-label="Fewer flashcards"
                        disabled={planFlow.busy || planFlow.count <= 1}
                        onClick={() => setPlanFlow({ ...planFlow, count: Math.max(1, planFlow.count - 1) })}
                        className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                      >
                        −
                      </button>
                      <span aria-live="polite" className="font-mono-data min-w-8 text-center text-xl font-bold text-slate-900">
                        {planFlow.count}
                      </span>
                      <button
                        type="button"
                        aria-label="More flashcards"
                        disabled={planFlow.busy || planFlow.count >= 20}
                        onClick={() => setPlanFlow({ ...planFlow, count: Math.min(20, planFlow.count + 1) })}
                        className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-lg text-slate-600 hover:bg-slate-50 disabled:opacity-30"
                      >
                        +
                      </button>
                      <button
                        type="button"
                        onClick={() => void generatePlannedFlashcards()}
                        disabled={planFlow.busy}
                        className="ml-1 flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {planFlow.busy && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
                        {planFlow.busy ? "Starting…" : "Start review"}
                      </button>
                    </div>
                    {planFlow.error && <p className="mt-2 text-xs text-red-600">{planFlow.error}</p>}
                  </div>
                )}
              </div>
            </div>
          )}
          {pending && (
            <div className="flex gap-3" role="status" aria-live="polite">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600">
                <BookOpen size={14} className="text-white" />
              </div>
              <div className="py-1">
                <p className="text-sm font-medium text-slate-700" key={thinkStep}>
                  {THINKING_STEPS[thinkStep]}
                </p>
                <div className="mt-2 flex gap-1">
                  {[0, 1, 2].map((d) => (
                    <div
                      key={d}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400"
                      style={{ animationDelay: `${d * 150}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        </div>

        <div className="flex gap-2 overflow-x-auto px-4 py-2 sm:px-6">
          {studyActions.map((a) => (
            <button
              key={a.label}
              type="button"
              className="shrink-0 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 transition-colors hover:bg-slate-100 disabled:opacity-50"
              onClick={() => a.run()}
              disabled={pending}
            >
              {a.label}
            </button>
          ))}
        </div>

        <div className="px-4 pb-4 pt-1 sm:px-6 sm:pb-6">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void ask(draft)
            }}
          >
            <div className="flex gap-2 rounded-xl border border-slate-200 bg-white p-3 transition focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-50">
              <input
                ref={inputRef}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask a question about your study material…"
                disabled={pending}
                aria-label="Ask the tutor"
                className="flex-1 text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
              <button
                type="submit"
                disabled={pending || !draft.trim()}
                aria-label="Ask the tutor"
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:opacity-40"
              >
                <Send size={14} />
              </button>
            </div>
          </form>
          <p className="mt-2 text-center text-xs text-slate-400">
            Answers are generated only from your uploaded study material.
          </p>
        </div>
      </div>

      {/* AREA 4 — Sources drawer (collapsible evidence panel) */}
      {sourcesOpen ? (
        <div className="hidden w-80 shrink-0 flex-col overflow-hidden border-l border-slate-200 bg-white sm:flex">
          <div className="flex items-start justify-between border-b border-slate-200 bg-white px-5 py-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-800">
                Sources{sources.length > 0 ? ` · ${sources.length} relevant` : ""}
              </h3>
              <p className="mt-0.5 text-xs text-slate-400">Referenced in the last response</p>
            </div>
            <button
              type="button"
              onClick={() => setSourcesOpen(false)}
              aria-label="Collapse sources panel"
              title="Collapse sources"
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
            >
              <ChevronRight size={15} />
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {sources.length === 0 ? (
              <p className="rounded-xl border border-slate-200 bg-white p-4 text-xs leading-relaxed text-slate-500">
                Citations from grounded answers will appear here with document name and page number.
              </p>
            ) : (
              sources.map((c) => (
                <div
                  key={c.chunk_id}
                  className={`cursor-pointer rounded-xl border bg-white p-4 shadow-sm transition-all ${
                    activeSource === c.chunk_id ? "border-indigo-200 ring-1 ring-indigo-100" : "border-slate-200 hover:border-slate-300"
                  }`}
                  onClick={() => setActiveSource(c.chunk_id)}
                >
                  <div className="mb-2 flex items-start gap-2.5">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <FileText size={12} className="shrink-0 text-red-400" />
                        <span className="truncate text-xs font-medium text-slate-700">{c.source_name ?? "material"}</span>
                      </div>
                      <div className="mt-0.5 text-xs text-slate-400">
                        {c.page_number != null ? `Page ${c.page_number}` : "Page —"}
                      </div>
                    </div>
                  </div>
                  {c.excerpt && (
                    <p className="border-l-2 border-indigo-200 pl-2.5 text-xs italic leading-relaxed text-slate-600">
                      …{c.excerpt.replace(/…+$/, "")}…
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setSourcesOpen(true)}
          aria-label={`Open sources panel${sources.length > 0 ? `, ${sources.length} relevant sources` : ""}`}
          title="Open sources"
          className="hidden w-10 shrink-0 flex-col items-center gap-2 border-l border-slate-200 bg-white py-4 text-slate-500 transition-colors hover:text-slate-700 sm:flex"
        >
          <FileText size={15} />
          <span className="text-[11px] font-bold [writing-mode:vertical-rl] rotate-180">
            Sources{sources.length > 0 ? ` · ${sources.length}` : ""}
          </span>
        </button>
      )}
      </div>
    </div>
  )
}
