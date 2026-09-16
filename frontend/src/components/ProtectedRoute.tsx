import { Navigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-2.5 bg-slate-50 text-sm text-slate-500">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
        Loading your study space…
      </div>
    )
  }
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
