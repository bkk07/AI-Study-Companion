import { Navigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth()
  if (loading) {
    return <div className="p-8 text-sm text-muted-foreground">Loading…</div>
  }
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
