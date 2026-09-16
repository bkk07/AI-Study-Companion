import { BrowserRouter, Routes, Route, Link } from "react-router-dom"
import { AuthProvider, useAuth } from "@/context/AuthContext"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { Login } from "@/features/auth/Login"
import { Register } from "@/features/auth/Register"
import { AdminPage } from "@/features/admin/AdminPage"
import { SpacesPage } from "@/features/spaces/SpacesPage"
import { SpaceProjectsPage } from "@/features/projects/SpaceProjectsPage"
import { ProjectDetailPage } from "@/features/projects/ProjectDetailPage"

function Home() {
  const { user, logout, token } = useAuth()
  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">AI Study Companion</h1>
        <div className="flex gap-2 text-sm">
          {!token ? (
            <>
              <Link to="/login" className="rounded-md border px-3 py-1 hover:bg-muted">
                Sign in
              </Link>
              <Link to="/register" className="rounded-md bg-primary px-3 py-1 text-primary-foreground hover:bg-primary/90">
                Sign up
              </Link>
            </>
          ) : (
            <button onClick={logout} className="rounded-md border px-3 py-1 hover:bg-muted">
              Sign out
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 text-muted-foreground">
        Project-scoped learning partner — upload PDFs, get a structured Topic → Subtopic → Concept map, and keep mastery isolated per project.
      </p>
      {user && (
        <div className="mt-4 rounded-md border bg-card p-3 text-sm">
          Signed in as <span className="font-medium">{user.email}</span> {user.is_admin && "(admin)"}
        </div>
      )}
      <div className="mt-6 flex gap-4 text-sm">
        <Link to="/" className="font-medium text-primary underline-offset-4 hover:underline">
          Home
        </Link>
        {token ? (
          <>
            <Link to="/dashboard" className="text-primary hover:underline">
              Dashboard
            </Link>
            <Link to="/spaces" className="text-primary hover:underline">
              Spaces
            </Link>
            {user?.is_admin && (
              <Link to="/admin" className="text-primary hover:underline">
                Admin
              </Link>
            )}
          </>
        ) : (
          <span className="text-muted-foreground">Dashboard (protected)</span>
        )}
      </div>
      <div className="mt-8 rounded-lg border bg-card p-4">
        <p className="text-sm text-muted-foreground">
          Auth is now connected. API client attaches <code className="rounded bg-muted px-1 py-0.5">Authorization: Bearer</code> from <code className="rounded bg-muted px-1 py-0.5">localStorage</code>; expired tokens auto-clear and redirect to /login.
        </p>
      </div>
    </div>
  )
}

function Dashboard() {
  const { user } = useAuth()
  return (
    <div className="mx-auto max-w-3xl p-8">
      <h2 className="text-xl font-semibold">Dashboard</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Protected route — only visible with a valid JWT. User: {user?.email}
      </p>
      <div className="mt-4 flex gap-4 text-sm">
        <Link to="/" className="text-primary hover:underline">
          Back home
        </Link>
        <Link to="/spaces" className="text-primary hover:underline">
          Spaces
        </Link>
      </div>
    </div>
  )
}

function NotFound() {
  return (
    <div className="mx-auto max-w-3xl p-8">
      <h2 className="text-xl font-semibold">Page not found</h2>
      <Link to="/" className="text-sm text-primary hover:underline">
        Go home
      </Link>
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
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
