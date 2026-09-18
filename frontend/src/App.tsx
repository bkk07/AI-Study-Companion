import { BrowserRouter, Routes, Route, Link, Navigate } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { AuthProvider, useAuth } from "@/context/AuthContext"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { AppShell } from "@/components/AppShell"
import { HomeDashboard } from "@/features/home/HomeDashboard"
import { LandingPage } from "@/features/landing/LandingPage"
import { Login } from "@/features/auth/Login"
import { Register } from "@/features/auth/Register"
import { AdminPage } from "@/features/admin/AdminPage"
import { SpacesPage } from "@/features/spaces/SpacesPage"
import { SpaceProjectsPage } from "@/features/projects/SpaceProjectsPage"
import { ProjectDetailPage } from "@/features/projects/ProjectDetailPage"

function Home() {
  const { user, token } = useAuth()
  if (!token) return <LandingPage />
  // Admins live in /admin — no student home, no spaces nav.
  if (user?.is_admin) return <Navigate to="/admin" replace />

  return (
    <AppShell>
      <HomeDashboard />
    </AppShell>
  )
}

function NotFound() {
  return (
    <AppShell>
      <div className="mx-auto max-w-2xl bg-slate-50 px-4 py-24 text-center sm:px-6">
        <p className="font-mono-data text-7xl font-bold text-slate-900">404</p>
        <h2 className="mt-4 text-2xl font-semibold text-slate-900">This page went off to study</h2>
        <p className="mt-2 text-sm text-slate-500">The link might be wrong, or the page moved.</p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Go home <ArrowRight size={16} />
        </Link>
      </div>
    </AppShell>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      {/* Single-mounted shell: navigating between these pages no longer
          remounts AppShell (streak/space-name refetch) every time. */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/spaces" element={<SpacesPage />} />
        <Route path="/spaces/:spaceId" element={<SpaceProjectsPage />} />
        <Route path="/spaces/:spaceId/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
