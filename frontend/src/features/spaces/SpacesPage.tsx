import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"

type Space = { id: string; name: string; created_at: string }

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
      const msg = apiError(e).message ?? "Failed to load spaces"
      setError(msg)
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
      setFieldError("Name is required")
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
      const msg = apiError(e).message ?? "Failed to create space"
      setError(msg)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Spaces</h1>
        <Link to="/" className="text-sm text-primary hover:underline">
          Home
        </Link>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">User → Space → Project hierarchy — create a space to hold projects.</p>

      <form onSubmit={onCreate} className="mt-6 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New space name"
          className="flex h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <button
          type="submit"
          disabled={creating}
          className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50"
        >
          {creating ? "Creating…" : "Create"}
        </button>
      </form>
      {fieldError && <p className="mt-2 text-sm text-destructive">{fieldError}</p>}
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}

      <div className="mt-6 rounded-lg border bg-card">
        {loading ? (
          <p className="p-4 text-sm text-muted-foreground">Loading…</p>
        ) : spaces.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">No spaces yet — create your first space above.</p>
            <button onClick={fetchSpaces} className="mt-2 text-sm text-primary hover:underline">
              Retry
            </button>
          </div>
        ) : (
          <ul className="divide-y">
            {spaces.map((s) => (
              <li key={s.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleString()}</p>
                </div>
                <Link to={`/spaces/${s.id}`} className="text-sm text-primary hover:underline">
                  Open →
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
