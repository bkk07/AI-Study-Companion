import { useState } from "react"
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
  | { kind: "user"; text: string }
  | { kind: "assistant"; answer: string; supported: boolean; citations: Citation[] }
  | { kind: "failure"; text: string; question: string }

function failureText(status?: number, detail?: string): string {
  if (status === 502) return "Tutor AI provider unavailable — no answer was generated. Retry when ready."
  if (status === 404) return "Project not found for this tutor session."
  return detail ?? "Failed to reach the tutor — no answer was generated."
}

export function TutorChat({ projectId }: { projectId: string }) {
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
    <div className="mt-2">
      <div className="space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Ask a question about this project's materials — answers come only from your uploads, with citations.
          </p>
        )}
        {messages.map((msg, i) =>
          msg.kind === "user" ? (
            <div key={i} className="ml-auto max-w-[85%] rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground">
              {msg.text}
            </div>
          ) : msg.kind === "assistant" ? (
            <div
              key={i}
              className={
                msg.supported
                  ? "max-w-[95%] rounded-md border bg-card px-3 py-2 text-sm"
                  : "max-w-[95%] rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm"
              }
            >
              {!msg.supported && <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-600">Not covered by your materials</p>}
              <p className="whitespace-pre-wrap">{msg.answer}</p>
              {msg.supported && msg.citations.length > 0 && (
                <ul className="mt-2 space-y-1 border-t pt-2 text-xs text-muted-foreground">
                  {msg.citations.map((c) => (
                    <li key={c.chunk_id}>
                      [{c.chunk_index}] {c.source_name ?? "material"}
                      {c.page_number != null ? `, page ${c.page_number}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div key={i} className="max-w-[95%] rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm">
              <p className="text-destructive">{msg.text}</p>
              <button
                type="button"
                onClick={() => void ask(msg.question)}
                disabled={pending}
                className="mt-1 text-sm text-primary hover:underline disabled:opacity-50"
              >
                Retry
              </button>
            </div>
          ),
        )}
        {pending && <p className="text-sm text-muted-foreground">Thinking…</p>}
      </div>
      <form
        className="mt-3 flex gap-2"
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
          className="flex-1 rounded-md border bg-background px-3 py-2 text-sm disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={pending || !draft.trim()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  )
}
