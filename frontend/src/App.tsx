import { BrowserRouter, Routes, Route, Link } from "react-router-dom"

function Home() {
  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold tracking-tight">AI Study Companion</h1>
      <p className="mt-2 text-muted-foreground">
        Project-scoped learning partner — upload PDFs, get a structured Topic → Subtopic → Concept map, and keep mastery, retrieval, and recommendations isolated per project.
      </p>
      <div className="mt-6 flex gap-4">
        <Link
          to="/"
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          Home
        </Link>
        <span className="text-sm text-muted-foreground">
          Auth, spaces, and projects arrive in later phases.
        </span>
      </div>
      <div className="mt-8 rounded-lg border bg-card p-4">
        <p className="text-sm text-muted-foreground">
          Frontend shell is initialized (Vite + React + TypeScript + Tailwind + shadcn/ui + React Router + Axios).
          API client is centralized in <code className="rounded bg-muted px-1 py-0.5">src/lib/axios.ts</code> and points at <code className="rounded bg-muted px-1 py-0.5">VITE_API_BASE_URL</code>.
        </p>
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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
