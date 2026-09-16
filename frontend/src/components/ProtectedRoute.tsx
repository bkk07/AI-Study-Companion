import { Navigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth()
  if (loading) {
    return (
      <div className="bg-mesh flex min-h-screen items-center justify-center gap-2.5 text-sm text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin text-violet-500" />
        Loading your study space…
      </div>
    )
  }
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
