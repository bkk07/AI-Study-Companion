import { BrowserRouter, Routes, Route, Link } from "react-router-dom"
import { ArrowRight, FolderKanban, MessagesSquare, ShieldCheck, Wand2 } from "lucide-react"
import { AuthProvider, useAuth } from "@/context/AuthContext"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { AppShell } from "@/components/AppShell"
import { Card, SectionHeader } from "@/components/ui"
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

  const cards = [
    {
      to: "/spaces",
      icon: FolderKanban,
      title: "My spaces",
      text: "Organize subjects into spaces, then projects. Pick up exactly where you left off.",
    },
    {
      to: "/spaces",
      icon: MessagesSquare,
      title: "Ask the tutor",
      text: "Open any project and chat with your materials — answers cite your uploads.",
    },
    {
      to: "/spaces",
      icon: Wand2,
      title: "Quiz yourself",
      text: "Generate adaptive quizzes tuned to your weakest concepts.",
    },
  ]

  return (
    <AppShell>
      <div className="bg-slate-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <SectionHeader
            title={`Welcome back${user ? `, ${user.email.split("@")[0]}` : ""}`}
            subtitle="Your spaces hold every subject. Jump back in, or start something new."
          />
          <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((c) => (
              <Link key={c.title} to={c.to}>
                <Card className="group h-full p-6 transition-all hover:border-slate-300 hover:shadow-sm">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <c.icon size={18} />
                  </span>
                  <h3 className="mt-4 flex items-center gap-1.5 text-base font-semibold text-slate-900">
                    {c.title}
                    <ArrowRight size={14} className="text-indigo-500 transition-transform group-hover:translate-x-1" />
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{c.text}</p>
                </Card>
              </Link>
            ))}
          </div>
          {user?.is_admin && (
            <Link to="/admin" className="mt-6 flex items-center gap-2 text-sm font-medium text-indigo-600 hover:underline">
              <ShieldCheck size={16} /> Open admin overview
            </Link>
          )}
        </div>
      </div>
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
      <Route
        path="/spaces"
        element={
          <ProtectedRoute>
            <SpacesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/spaces/:spaceId"
        element={
          <ProtectedRoute>
            <SpaceProjectsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/spaces/:spaceId/projects/:projectId"
        element={
          <ProtectedRoute>
            <ProjectDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminPage />
          </ProtectedRoute>
        }
      />
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
