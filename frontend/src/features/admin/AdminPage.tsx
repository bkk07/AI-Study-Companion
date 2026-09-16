import { useCallback, useEffect, useState } from "react"
import {
  BookOpenText,
  BrainCircuit,
  FileUp,
  FolderKanban,
  GraduationCap,
  ShieldAlert,
  ShieldCheck,
  Trophy,
  Users,
  Wand2,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { useAuth } from "@/context/AuthContext"
import { AppShell } from "@/components/AppShell"
import { Avatar, Badge, Card, ErrorBox, LoadingState, PageHeader } from "@/components/ui"

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
      const { status, message: detail } = apiError(e)
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

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <PageHeader
          eyebrow="Operations"
          title={
            <span className="inline-flex items-center gap-2.5">
              <ShieldCheck className="h-8 w-8 text-violet-600" /> Admin overview
            </span>
          }
          description="Global usage counts and the user roster. Read-only."
        />
        <div className="mt-6">
          {loading ? (
            <LoadingState text="Loading admin…" />
          ) : error ? (
            <div className="max-w-2xl">
              <ErrorBox message={error} onRetry={() => void load()} />
              {error.startsWith("Forbidden") && (
                <p className="mt-3 flex items-center gap-1.5 text-sm text-muted-foreground">
                  <ShieldAlert className="h-4 w-4" /> This area requires an admin account.
                </p>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                {(
                  [
                    [Users, "Users", overview?.users ?? 0, "bg-violet-100 text-violet-600"],
                    [FolderKanban, "Spaces", overview?.spaces ?? 0, "bg-indigo-100 text-indigo-600"],
                    [GraduationCap, "Projects", overview?.projects ?? 0, "bg-fuchsia-100 text-fuchsia-600"],
                    [FileUp, "Materials", overview?.materials ?? 0, "bg-rose-100 text-rose-600"],
                    [Wand2, "Quizzes", overview?.quizzes ?? 0, "bg-amber-100 text-amber-600"],
                    [Trophy, "Quiz attempts", overview?.quiz_attempts ?? 0, "bg-emerald-100 text-emerald-600"],
                    [BrainCircuit, "Evidence rows", overview?.evidence_rows ?? 0, "bg-sky-100 text-sky-600"],
                    [BookOpenText, "Recommendations", overview?.recommendations ?? 0, "bg-teal-100 text-teal-600"],
                  ] as const
                ).map(([Icon, label, value, tint]) => (
                  <Card key={label} className="p-3.5">
                    <span className={`inline-flex h-8 w-8 items-center justify-center rounded-lg ${tint}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <p className="mt-2 text-2xl font-extrabold tracking-tight">{value}</p>
                    <p className="text-xs font-medium text-muted-foreground">{label}</p>
                  </Card>
                ))}
              </div>

              <h3 className="mt-8 text-lg font-extrabold tracking-tight">Users</h3>
              <Card className="mt-3 divide-y overflow-hidden">
                {(users ?? []).map((u) => (
                  <div key={u.id} className="flex items-center gap-3 px-4 py-3">
                    <Avatar email={u.email} className="h-8 w-8 text-xs" />
                    <span className="min-w-0 flex-1 truncate text-sm font-semibold">{u.email}</span>
                    <Badge tint={u.is_admin ? "violet" : "muted"}>{u.is_admin ? "admin" : "user"}</Badge>
                    <span className="hidden text-xs text-muted-foreground sm:inline">
                      {new Date(u.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </Card>
            </>
          )}
        </div>
      </div>
    </AppShell>
  )
}
