import React, { useEffect, useRef, useState } from "react"
import {
  BookOpen,
  BookOpenCheck,
  Brain,
  Check,
  Copy,
  FileText,
  History,
  Lightbulb,
  Pin,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import "katex/dist/katex.min.css"
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

/** Wrap valid [n] citation markers in backticks (outside fenced code blocks) so
 * they parse as inline code and can be rendered as clickable links in flow. */
function markCitations(source: string, valid: Set<number>): string {
  return source
    .split(/(```[\s\S]*?```)/g)
    .map((seg, i) => {
      if (i % 2 === 1) return seg // fenced block — untouched
      return seg.replace(/\[(\d+)\]/g, (m, n) => (valid.has(parseInt(n, 10)) ? `\`${m}\`` : m))
    })
    .join("")
}

const mdBaseComponents = {
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

/** Citation-aware `code` renderer: `[n]` markers become inline source links. */
function citeCodeRenderer(
  citations: Citation[],
  onCite: (c: Citation) => void,
) {
  return ({ className, children }: { className?: string; children?: React.ReactNode }) => {
    const text = React.Children.toArray(children).join("").toString()
    if (text.includes("\n")) return <code className={className}>{children}</code>
    const match = text.match(/^\[(\d+)\]$/)
    const cit = match ? citations.find((c) => c.chunk_index === parseInt(match[1], 10)) : undefined
    if (match && cit) {
      const idx = match[1]
      const label = `${cit.source_name ?? "Source"}${cit.page_number != null ? ` · Page ${cit.page_number}` : ""}`
      return (
        <button
          type="button"
          title={label}
          aria-label={`Source ${idx}: ${label}`}
          onClick={() => onCite(cit)}
          className="mx-px inline rounded px-0.5 align-baseline text-[13px] font-bold text-indigo-600 underline decoration-indigo-300 decoration-[1.5px] underline-offset-[3px] transition-colors hover:bg-indigo-50 hover:text-indigo-800 hover:decoration-indigo-600"
        >
          [{idx}]
        </button>
      )
    }
    return (
      <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono-data text-[13px] text-slate-800">
        {children}
      </code>
    )
  }
}

/** Render markdown with [n] citation markers as inline clickable source links. */
function AnswerBody({
  answer,
  citations,
  onCite,
}: {
  answer: string
  citations: Citation[]
  onCite: (c: Citation) => void
}) {
  const valid = React.useMemo(
    () => new Set(citations.map((c) => c.chunk_index)),
    [citations],
  )
  const source = React.useMemo(() => markCitations(answer, valid), [answer, valid])
  const components = React.useMemo(
    () => ({ ...mdBaseComponents, code: citeCodeRenderer(citations, onCite) }),
    [citations, onCite],
  )
  return (
    <div className="tutor-math space-y-3">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={components}
      >
        {source}
      </ReactMarkdown>
    </div>
  )
}

/* ---------- Main chat ---------- */

export function TutorChat({
  projectId,
  onQuizMe,
  onFlashcards,
}: {
  projectId: string
  onQuizMe?: () => void
  onFlashcards?: () => void
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
  const [listOpen, setListOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const thinkTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => () => {
    if (thinkTimer.current) clearInterval(thinkTimer.current)
  }, [])

  const lastUserQuestion = [...messages].reverse().find((m) => m.kind === "user")?.text ?? null

  const refreshList = async () => {
    try {
      const res = await apiClient.get<Conversation[]>(`/projects/${projectId}/tutor/conversations`)
      setConvos(res.data)
    } catch {
      setConvos([])
    }
  }

  const openConversation = async (id: string) => {
    setListOpen(false)
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
    setListOpen(false)
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
    setListOpen(false)
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

  const scrollToSource = (c: Citation) => {
    setActiveSource(c.chunk_id)
    requestAnimationFrame(() => {
      document
        .getElementById(`panel-tutor-src-${c.chunk_id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    })
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
    { label: "Explain simply", run: () => lastUserQuestion && void ask(`Explain simply: ${lastUserQuestion}`) },
    { label: "Explain deeply", run: () => lastUserQuestion && void ask(`Explain in depth: ${lastUserQuestion}`) },
    { label: "Give example", run: () => lastUserQuestion && void ask(`Give an example — in the context of: "${lastUserQuestion}"`) },
    { label: "Summarize", run: () => lastUserQuestion && void ask(`Summarize — in the context of: "${lastUserQuestion}"`) },
    { label: "Quiz me", run: () => (onQuizMe ? onQuizMe() : lastUserQuestion && void ask(`Quiz me on: ${lastUserQuestion}`)) },
    { label: "Flashcards", run: () => (onFlashcards ? onFlashcards() : lastUserQuestion && void ask(`Give me flashcard-style key points for: ${lastUserQuestion}`)) },
  ]

  const lastAssistant = [...messages].reverse().find((m) => m.kind === "assistant") as
    | { kind: "assistant"; citations: Citation[] }
    | undefined
  const sources = lastAssistant?.citations ?? []
  const activeTitle = convos?.find((c) => c.id === activeId)?.title ?? "New chat"

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <div className="relative min-w-0">
          <button
            type="button"
            onClick={() => setListOpen((o) => !o)}
            aria-haspopup="menu"
            aria-expanded={listOpen}
            className="flex max-w-64 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
          >
            <History size={14} className="shrink-0 text-slate-400" />
            <span className="truncate">{historyLoading ? "Loading chat…" : activeTitle}</span>
          </button>
          {listOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setListOpen(false)} aria-hidden />
              <div role="menu" aria-label="Previous chats" className="absolute left-0 top-11 z-50 max-h-80 w-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg">
                {convos === null ? (
                  <p className="px-3 py-4 text-center text-xs text-slate-400">Loading chats…</p>
                ) : convos.length === 0 ? (
                  <p className="px-3 py-4 text-center text-xs text-slate-400">No previous chats yet — ask something to start one.</p>
                ) : (
                  convos.map((c) => (
                    <div
                      key={c.id}
                      role="menuitem"
                      className={`group flex items-center gap-1 rounded-lg px-2 py-2 transition-colors hover:bg-slate-50 ${
                        c.id === activeId ? "bg-indigo-50/60" : ""
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => void openConversation(c.id)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <span className="block truncate text-sm font-medium text-slate-800">{c.title}</span>
                        <span className="block text-[11px] text-slate-400">
                          {fmtDate(c.updated_at)}
                          {c.message_count > 0 ? ` · ${Math.ceil(c.message_count / 2)} exchange${c.message_count > 2 ? "s" : ""}` : ""}
                        </span>
                      </button>
                      <button
                        type="button"
                        aria-label={`Delete chat ${c.title}`}
                        onClick={() => void deleteChat(c.id)}
                        className="rounded p-1.5 text-slate-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={newChat}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
        >
          <Plus size={14} /> New chat
        </button>
      </div>
      <div className="flex overflow-hidden rounded-xl border border-slate-200 bg-white" style={{ height: "640px" }}>
      <div className="flex min-w-0 flex-1 flex-col border-r border-slate-200">
        <div className="flex-1 space-y-6 overflow-y-auto px-4 py-6 sm:px-6" aria-live="polite">
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
                      <AnswerBody answer={msg.answer} citations={msg.citations} onCite={scrollToSource} />

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
                          <div className="flex gap-2 overflow-x-auto pb-1">
                            {msg.followUps.map((f, k) => (
                              <button
                                key={k}
                                type="button"
                                disabled={pending}
                                onClick={() => void ask(f)}
                                className="shrink-0 rounded-full border border-indigo-200 bg-indigo-50/60 px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-50"
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

      <div className="hidden w-80 shrink-0 overflow-y-auto bg-slate-50 sm:block">
        <div className="border-b border-slate-200 bg-white px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-800">
            Sources{sources.length > 0 ? ` · ${sources.length} relevant` : ""}
          </h3>
          <p className="mt-0.5 text-xs text-slate-400">Referenced in the last response</p>
        </div>
        <div className="space-y-3 p-4">
          {sources.length === 0 ? (
            <p className="rounded-xl border border-slate-200 bg-white p-4 text-xs leading-relaxed text-slate-500">
              Citations from grounded answers will appear here with document name and page number.
            </p>
          ) : (
            sources.map((c) => (
              <div
                key={c.chunk_id}
                id={`panel-tutor-src-${c.chunk_id}`}
                className={`cursor-pointer rounded-xl border bg-white p-4 transition-all ${
                  activeSource === c.chunk_id ? "border-indigo-200 ring-1 ring-indigo-100" : "border-slate-200 hover:border-slate-300"
                }`}
                onClick={() => setActiveSource(c.chunk_id)}
              >
                <div className="mb-2 flex items-start gap-2.5">
                  <sup className="mt-0.5 text-xs font-bold text-indigo-600">[{c.chunk_index}]</sup>
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
      </div>
    </div>
  )
}
