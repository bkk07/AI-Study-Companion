import { useRef, useState } from "react"
import { BookOpen, BookOpenCheck, ChevronRight, FileText, HelpCircle, Lightbulb, Minimize2, Repeat, Send, Sparkles } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"

type Citation = {
  chunk_id: string
  material_id: string
  page_number: number | null
  source_name: string | null
  chunk_index: number
}

type AskResponse = {
  answer: string
  supported: boolean
  citations: Citation[]
}

type Message =
  | { kind: "user"; text: string; time: string }
  | { kind: "assistant"; answer: string; supported: boolean; citations: Citation[]; time: string }
  | { kind: "failure"; text: string; question: string }

function failureText(status?: number, detail?: string): string {
  if (status === 429) return "Slow down — too many tutor requests. Wait a moment and retry."
  if (status === 502) return "Tutor AI provider unavailable — no answer was generated. Retry when ready."
  if (status === 404) return "Project not found for this tutor session."
  return detail ?? "Failed to reach the tutor — no answer was generated."
}

const QUICK_ACTIONS = [
  { label: "Explain simpler", icon: <Minimize2 size={13} /> },
  { label: "Give an example", icon: <Lightbulb size={13} /> },
  { label: "Compare concepts", icon: <Repeat size={13} /> },
  { label: "Summarize", icon: <BookOpen size={13} /> },
  { label: "Quiz me on this", icon: <HelpCircle size={13} /> },
]

function now(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function TutorChat({ projectId }: { projectId: string }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      kind: "assistant",
      answer: "Hello! I'm your AI tutor for this project. I answer only from your uploaded study material. What would you like to explore?",
      supported: true,
      citations: [],
      time: now(),
    },
  ])
  const [draft, setDraft] = useState("")
  const [pending, setPending] = useState(false)
  const [activeSource, setActiveSource] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function ask(question: string) {
    const q = question.trim()
    if (!q || pending) return
    setPending(true)
    setDraft("")
    setMessages((m) => [...m, { kind: "user", text: q, time: now() }])
    try {
      const res = await apiClient.post<AskResponse>(`/projects/${projectId}/tutor/ask`, { question: q })
      setMessages((m) => [
        ...m,
        { kind: "assistant", answer: res.data.answer, supported: res.data.supported, citations: res.data.citations, time: now() },
      ])
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setMessages((m) => [...m, { kind: "failure", text: failureText(status, detail), question: q }])
    } finally {
      setPending(false)
    }
  }

  const renderText = (text: string, citations: Citation[]) => {
    if (citations.length === 0) return <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{text}</p>
    const parts = text.split(/(\[\d+\])/g)
    return (
      <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">
        {parts.map((part, i) => {
          const match = part.match(/^\[(\d+)\]$/)
          if (match) {
            const idx = parseInt(match[1], 10)
            const cit = citations.find((c) => c.chunk_index === idx)
            return (
              <sup
                key={i}
                className="ml-0.5 cursor-pointer font-semibold text-indigo-600 hover:underline"
                onClick={() => cit && setActiveSource(cit.chunk_id)}
              >
                {part}
              </sup>
            )
          }
          return <span key={i}>{part}</span>
        })}
      </p>
    )
  }

  const lastAssistant = [...messages].reverse().find((m) => m.kind === "assistant") as
    | { kind: "assistant"; citations: Citation[] }
    | undefined
  const sources = lastAssistant?.citations ?? []

  return (
    <div className="flex overflow-hidden rounded-xl border border-slate-200 bg-white" style={{ height: "640px" }}>
      <div className="flex min-w-0 flex-1 flex-col border-r border-slate-200">
        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
          {messages.map((msg, i) =>
            msg.kind === "user" ? (
              <div key={i} className="flex flex-row-reverse gap-4">
                <div className="ml-auto max-w-lg">
                  <div className="rounded-xl bg-indigo-600 px-4 py-3 text-sm text-white">
                    <p className="leading-relaxed">{msg.text}</p>
                  </div>
                  <div className="mt-1 px-1 text-xs text-slate-400">{msg.time}</div>
                </div>
              </div>
            ) : msg.kind === "assistant" ? (
              <div key={i} className="flex gap-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600">
                  <BookOpen size={14} className="text-white" />
                </div>
                <div className="max-w-lg">
                  <div className={`rounded-xl border px-4 py-3 ${msg.supported ? "border-slate-200 bg-white" : "border-amber-200 bg-amber-50"}`}>
                    {!msg.supported && (
                      <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
                        <BookOpenCheck size={14} /> Not covered by your materials
                      </p>
                    )}
                    {renderText(msg.answer, msg.citations)}
                  </div>
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
                  <button
                    type="button"
                    onClick={() => void ask(msg.question)}
                    disabled={pending}
                    className="mt-1 text-sm font-medium text-indigo-600 hover:underline disabled:opacity-50"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ),
          )}
          {pending && (
            <div className="flex gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600">
                <BookOpen size={14} className="text-white" />
              </div>
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map((d) => (
                    <div key={d} className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: `${d * 150}ms` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex flex-wrap gap-2 px-6 py-2">
          {QUICK_ACTIONS.map((a) => (
            <button
              key={a.label}
              type="button"
              className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 transition-colors hover:bg-slate-100"
              onClick={() => void ask(a.label)}
              disabled={pending}
            >
              {a.icon}{a.label}
            </button>
          ))}
        </div>

        <div className="px-6 pb-6 pt-2">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void ask(draft)
            }}
          >
            <div className="flex gap-2 rounded-xl border border-slate-200 bg-white p-3 transition focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-50">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask a question about your study material…"
                disabled={pending}
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
          <h3 className="text-sm font-semibold text-slate-800">Sources</h3>
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
                <button type="button" className="mt-2 flex items-center gap-1 text-xs text-indigo-600 hover:underline">
                  Open in document <ChevronRight size={11} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
