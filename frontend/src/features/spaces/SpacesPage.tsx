import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, FolderKanban, Plus } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { AppShell } from "@/components/AppShell"
import { Button, Card, EmptyState, ErrorBox, Input, LoadingState, PageHeader } from "@/components/ui"

type Space = { id: string; name: string; created_at: string }

const TILES = [
  "from-violet-500 to-purple-600",
  "from-fuchsia-500 to-pink-500",
  "from-indigo-500 to-blue-500",
  "from-emerald-500 to-teal-500",
  "from-amber-500 to-orange-500",
  "from-sky-500 to-cyan-500",
]

export function tileFor(id: string): string {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return TILES[h % TILES.length]
}

export function SpacesPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  const fetchSpaces = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<Space[]>("/spaces")
      setSpaces(res.data)
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to load spaces")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSpaces()
  }, [])

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setFieldError("Give your space a name first")
      return
    }
    setFieldError(null)
    setCreating(true)
    setError(null)
    try {
      await apiClient.post("/spaces", { name: name.trim() })
      setName("")
      await fetchSpaces()
    } catch (e: unknown) {
      setError(apiError(e).message ?? "Failed to create space")
    } finally {
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <PageHeader
          eyebrow="Library"
          title={
            <>
              My <span className="text-gradient">spaces</span>
            </>
          }
          description="One space per subject. Inside each: projects, PDFs, tutor chats, and quizzes."
        />

        <Card className="mt-6 p-4 sm:p-5">
          <form onSubmit={onCreate} className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="New space name — e.g. Linear Algebra"
              aria-label="New space name"
            />
            {fieldError && <p className="text-sm font-medium text-rose-600 sm:hidden">{fieldError}</p>}
            <Button type="submit" disabled={creating} className="shrink-0 px-5">
              <Plus className="h-4 w-4" />
              {creating ? "Creating…" : "New space"}
            </Button>
          </form>
          {fieldError && <p className="mt-2 hidden text-sm font-medium text-rose-600 sm:block">{fieldError}</p>}
        </Card>

        <div className="mt-6">
          {loading ? (
            <LoadingState text="Loading spaces…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void fetchSpaces()} />
          ) : spaces.length === 0 ? (
            <EmptyState
              icon={<FolderKanban className="h-6 w-6" />}
              title="No spaces yet"
              hint="Create your first space above — like a folder for everything about one subject."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {spaces.map((s, i) => (
                <Link key={s.id} to={`/spaces/${s.id}`}>
                  <Card
                    className="animate-fade-up stagger group h-full p-5 transition-all hover:-translate-y-1 hover:shadow-lift"
                    style={{ "--d": `${Math.min(i, 8) * 60}ms` } as React.CSSProperties}
                  >
                    <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-soft ${tileFor(s.id)}`}>
                      <FolderKanban className="h-6 w-6" />
                    </span>
                    <h3 className="mt-3.5 flex items-center gap-1.5 text-lg font-bold tracking-tight">
                      <span className="truncate">{s.name}</span>
                      <ArrowRight className="h-4 w-4 shrink-0 text-violet-500 transition-transform group-hover:translate-x-1" />
                    </h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Created {new Date(s.created_at).toLocaleDateString()}
                    </p>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
