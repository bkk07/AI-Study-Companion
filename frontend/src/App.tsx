import { BrowserRouter, Routes, Route, Link } from "react-router-dom"
import { ArrowRight, FolderKanban, MessagesSquare, ShieldCheck, Wand2 } from "lucide-react"
import { AuthProvider, useAuth } from "@/context/AuthContext"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { AppShell } from "@/components/AppShell"
import { Card, PageHeader } from "@/components/ui"
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
      tint: "from-violet-500 to-purple-600",
      title: "My spaces",
      text: "Organize subjects into spaces, then projects. Pick up exactly where you left off.",
    },
    {
      to: "/spaces",
      icon: MessagesSquare,
      tint: "from-fuchsia-500 to-pink-500",
      title: "Ask the tutor",
      text: "Open any project and chat with your materials — answers cite your uploads.",
    },
    {
      to: "/spaces",
      icon: Wand2,
      tint: "from-amber-500 to-orange-500",
      title: "Quiz yourself",
      text: "Generate adaptive quizzes tuned to your weakest concepts.",
    },
  ]

  return (
    <AppShell>
      <div className="bg-mesh">
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
          <PageHeader
            eyebrow={`Welcome back${user ? `, ${user.email.split("@")[0]}` : ""}`}
            title={
              <>
                What are we <span className="text-gradient">learning today?</span>
              </>
            }
            description="Your spaces hold every subject. Jump back in, or start something new."
          />
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((c, i) => (
              <Link key={c.title} to={c.to}>
                <Card
                  className="animate-fade-up stagger group h-full p-6 transition-all hover:-translate-y-1 hover:shadow-lift"
                  style={{ "--d": `${i * 80}ms` } as React.CSSProperties}
                >
                  <span className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-soft ${c.tint}`}>
                    <c.icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-4 flex items-center gap-1.5 font-bold">
                    {c.title}
                    <ArrowRight className="h-4 w-4 text-violet-500 transition-transform group-hover:translate-x-1" />
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{c.text}</p>
                </Card>
              </Link>
            ))}
          </div>
          {user?.is_admin && (
            <Link to="/admin" className="mt-4 flex items-center gap-2 text-sm font-semibold text-violet-700 hover:underline">
              <ShieldCheck className="h-4 w-4" /> Open admin overview
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
      <div className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6">
        <p className="text-7xl font-extrabold text-gradient">404</p>
        <h2 className="mt-4 text-2xl font-bold">This page went off to study</h2>
        <p className="mt-2 text-muted-foreground">The link might be wrong, or the page moved.</p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white shadow-soft hover:brightness-110"
        >
          Go home <ArrowRight className="h-4 w-4" />
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
