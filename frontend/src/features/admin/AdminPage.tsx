import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import apiClient from "@/lib/axios"
import { useAuth } from "@/context/AuthContext"

type AdminUser = {
  id: string
  email: string
  is_admin: boolean
  created_at: string
}

type Overview = {
  users: number
  spaces: number
  projects: number
  materials: number
  quizzes: number
  quiz_attempts: number
  evidence_rows: number
  recommendations: number
}

function extractError(e: unknown): { status?: number; detail?: string } {
  return {
    status: (e as { response?: { status?: number } }).response?.status,
    detail: (e as { response?: { data?: { detail?: string } } }).response?.data?.detail,
  }
}

export function AdminPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<AdminUser[] | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [u, o] = await Promise.all([
        apiClient.get<AdminUser[]>("/admin/users"),
        apiClient.get<Overview>("/admin/overview"),
      ])
      setUsers(u.data)
      setOverview(o.data)
    } catch (e: unknown) {
      const { status, detail } = extractError(e)
      if (status === 403) setError("Forbidden — admins only.")
      else setError(detail ?? "Failed to load admin data.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (user && !user.is_admin) {
      setLoading(false)
      setError("Forbidden — admins only.")
      return
    }
    if (user) void load()
  }, [user, load])

  if (loading) return <p className="mt-2 text-sm text-muted-foreground">Loading admin…</p>
  if (error)
    return (
      <div className="mx-auto max-w-3xl p-8">
        <p className="text-sm text-destructive">{error}</p>
        <div className="mt-2 flex gap-4 text-sm">
          <button onClick={() => void load()} className="text-primary hover:underline">
            Retry
          </button>
          <Link to="/" className="text-primary hover:underline">
            Go home
          </Link>
        </div>
      </div>
    )

  const cards: Array<[string, number]> = overview
    ? [
        ["Users", overview.users],
        ["Spaces", overview.spaces],
        ["Projects", overview.projects],
        ["Materials", overview.materials],
        ["Quizzes", overview.quizzes],
        ["Quiz attempts", overview.quiz_attempts],
        ["Evidence rows", overview.evidence_rows],
        ["Recommendations", overview.recommendations],
      ]
    : []

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h2 className="text-xl font-semibold">Admin</h2>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-md border bg-card px-3 py-2">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-lg font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <h3 className="mt-6 text-lg font-semibold">Users</h3>
      <ul className="mt-2 space-y-1">
        {(users ?? []).map((u) => (
          <li key={u.id} className="flex justify-between rounded-md border bg-card px-3 py-2 text-sm">
            <span>{u.email}</span>
            <span className="text-muted-foreground">
              {u.is_admin ? "admin" : "user"} · {new Date(u.created_at).toLocaleDateString()}
            </span>
          </li>
        ))}
      </ul>
      <Link to="/" className="mt-4 inline-block text-sm text-primary hover:underline">
        Back home
      </Link>
    </div>
  )
}
