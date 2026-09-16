import { useState } from "react"
import { BookOpenCheck, SendHorizonal, Sparkles } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Avatar } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { cn } from "@/lib/utils"

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
  | { kind: "user"; text: string }
  | { kind: "assistant"; answer: string; supported: boolean; citations: Citation[] }
  | { kind: "failure"; text: string; question: string }

function failureText(status?: number, detail?: string): string {
  if (status === 429) return "Slow down — too many tutor requests. Wait a moment and retry."
  if (status === 502) return "Tutor AI provider unavailable — no answer was generated. Retry when ready."
  if (status === 404) return "Project not found for this tutor session."
  return detail ?? "Failed to reach the tutor — no answer was generated."
}

const SUGGESTIONS = [
  "Summarize the key ideas",
  "Quiz me on the hardest part",
  "Explain it like I'm five",
]

export function TutorChat({ projectId }: { projectId: string }) {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState("")
  const [pending, setPending] = useState(false)

  async function ask(question: string) {
    const q = question.trim()
    if (!q || pending) return
    setPending(true)
    setDraft("")
    setMessages((m) => [...m, { kind: "user", text: q }])
    try {
      const res = await apiClient.post<AskResponse>(`/projects/${projectId}/tutor/ask`, { question: q })
      setMessages((m) => [
        ...m,
        { kind: "assistant", answer: res.data.answer, supported: res.data.supported, citations: res.data.citations },
      ])
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      setMessages((m) => [...m, { kind: "failure", text: failureText(status, detail), question: q }])
    } finally {
      setPending(false)
    }
  }

  return (
    <div>
      <div className="space-y-4">
        {messages.length === 0 && (
          <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 p-5 text-white shadow-soft sm:p-6">
            <p className="flex items-center gap-2 font-bold">
              <Sparkles className="h-5 w-5" /> Ask me anything about your materials
            </p>
            <p className="mt-1 text-sm text-white/80">
              Answers come only from your uploads — with citations to the exact source.
            </p>
            <div className="mt-3.5 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void ask(s)}
                  disabled={pending}
                  className="rounded-full bg-white/15 px-3.5 py-1.5 text-xs font-semibold backdrop-blur transition-all hover:bg-white/25 disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) =>
          msg.kind === "user" ? (
            <div key={i} className="flex items-end justify-end gap-2">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-2.5 text-sm text-white shadow-soft">
                {msg.text}
              </div>
              {user && <Avatar email={user.email} className="h-7 w-7 text-[11px]" />}
            </div>
          ) : msg.kind === "assistant" ? (
            <div key={i} className="flex items-end gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white">
                <Sparkles className="h-3.5 w-3.5" />
              </span>
              <div
                className={cn(
                  "max-w-[92%] rounded-2xl rounded-bl-md px-4 py-2.5 text-sm shadow-soft",
                  msg.supported ? "border bg-card" : "border border-amber-300 bg-amber-50",
                )}
              >
                {!msg.supported && (
                  <p className="mb-1 flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-amber-700">
                    <BookOpenCheck className="h-3.5 w-3.5" /> Not covered by your materials
                  </p>
                )}
                <p className="whitespace-pre-wrap leading-relaxed">{msg.answer}</p>
                {msg.supported && msg.citations.length > 0 && (
                  <ul className="mt-2.5 space-y-1 border-t border-dashed pt-2 text-xs text-muted-foreground">
                    {msg.citations.map((c) => (
                      <li key={c.chunk_id}>
                        <span className="font-bold text-violet-600">[{c.chunk_index}]</span>{" "}
                        {c.source_name ?? "material"}
                        {c.page_number != null ? `, page ${c.page_number}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ) : (
            <div key={i} className="max-w-[92%] rounded-2xl rounded-bl-md border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm">
              <p className="font-medium text-rose-700">{msg.text}</p>
              <button
                type="button"
                onClick={() => void ask(msg.question)}
                disabled={pending}
                className="mt-1 text-sm font-bold text-violet-700 hover:underline disabled:opacity-50"
              >
                Retry
              </button>
            </div>
          ),
        )}
        {pending && (
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <div className="flex items-center gap-1 rounded-2xl rounded-bl-md border bg-card px-4 py-3 shadow-soft">
              {[0, 1, 2].map((d) => (
                <span key={d} className="typing-dot h-2 w-2 rounded-full bg-violet-500" />
              ))}
            </div>
          </div>
        )}
      </div>
      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          void ask(draft)
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about your materials…"
          disabled={pending}
          className="flex-1 rounded-2xl border border-input bg-background px-4 py-3 text-sm shadow-sm transition-all placeholder:text-muted-foreground/70 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-500/15 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={pending || !draft.trim()}
          aria-label="Ask the tutor"
          className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-2xl bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-soft transition-all hover:shadow-lift hover:brightness-110 disabled:opacity-50"
        >
          <SendHorizonal className="h-5 w-5" />
        </button>
      </form>
    </div>
  )
}
