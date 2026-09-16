import { useCallback, useEffect, useState } from "react"
import {
  BookOpenText,
  BrainCircuit,
  CreditCard,
  FileUp,
  FolderOpen,
  HelpCircle,
  MessageCircle,
  ShieldAlert,
  ShieldCheck,
  Users,
} from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { useAuth } from "@/context/AuthContext"
import { AppShell } from "@/components/AppShell"
import { Avatar, ErrorBox, LoadingState } from "@/components/ui"
import { MoreHorizontal } from "lucide-react"

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
      <div className="mx-auto max-w-5xl bg-slate-50 px-8 py-10">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-400">Admin</div>
            <h1 className="text-xl font-semibold text-slate-900">System Overview</h1>
          </div>
        </div>
        <div>
          {loading ? (
            <LoadingState text="Loading admin…" />
          ) : error ? (
            <div className="max-w-2xl">
              <ErrorBox message={error} onRetry={() => void load()} />
              {error.startsWith("Forbidden") && (
                <p className="mt-3 flex items-center gap-1.5 text-sm text-slate-500">
                  <ShieldAlert size={16} /> This area requires an admin account.
                </p>
              )}
            </div>
          ) : (
            <>
              <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {[
                  { label: "Users", value: overview?.users ?? 0, icon: <Users size={16} /> },
                  { label: "Projects", value: overview?.projects ?? 0, icon: <FolderOpen size={16} /> },
                  { label: "Documents", value: overview?.materials ?? 0, icon: <FileUp size={16} /> },
                  { label: "Quiz Attempts", value: overview?.quiz_attempts ?? 0, icon: <HelpCircle size={16} /> },
                  { label: "Flashcard Reviews", value: overview?.evidence_rows ?? 0, icon: <CreditCard size={16} /> },
                  { label: "Tutor Questions", value: overview?.recommendations ?? 0, icon: <MessageCircle size={16} /> },
                ].map((s) => (
                  <div key={s.label} className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                    <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-600">
                      {s.icon}
                    </div>
                    <div className="font-mono-data text-2xl font-bold text-slate-900">{s.value.toLocaleString()}</div>
                    <div className="mt-0.5 text-xs text-slate-500">{s.label}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-50 text-slate-600">
                    <BookOpenText size={16} />
                  </div>
                  <div className="font-mono-data mt-2 text-2xl font-bold text-slate-900">{overview?.spaces ?? 0}</div>
                  <div className="text-xs text-slate-500">Spaces</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-50 text-slate-600">
                    <BrainCircuit size={16} />
                  </div>
                  <div className="font-mono-data mt-2 text-2xl font-bold text-slate-900">{overview?.quizzes ?? 0}</div>
                  <div className="text-xs text-slate-500">Quizzes</div>
                </div>
              </div>

              <div className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div className="border-b border-slate-100 px-6 py-4">
                  <h2 className="text-sm font-semibold text-slate-800">Users</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Joined</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Role</th>
                        <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(users ?? []).map((u, i) => (
                        <tr key={u.id} className={`border-b border-slate-50 transition-colors hover:bg-slate-50 ${i === (users ?? []).length - 1 ? "border-0" : ""}`}>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <Avatar email={u.email} className="h-8 w-8 text-xs" />
                              <span className="font-medium text-slate-800">{u.email.split("@")[0]}</span>
                            </div>
                          </td>
                          <td className="px-4 py-4 text-slate-500">{u.email}</td>
                          <td className="px-4 py-4 text-xs text-slate-500">{new Date(u.created_at).toLocaleDateString()}</td>
                          <td className="px-4 py-4">
                            {u.is_admin ? (
                              <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-medium text-white">Admin</span>
                            ) : (
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Student</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button type="button" className="rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700">
                              <MoreHorizontal size={15} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  )
}
