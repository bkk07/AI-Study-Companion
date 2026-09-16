import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AlertCircle, ArrowRight, BookOpen, Brain, Eye, EyeOff, Loader2, Network } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { authErrorMessage } from "@/lib/api-error"
import { KnowledgeGraphSVG } from "@/components/KnowledgeGraph"

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!email || !password) {
      setError("Please enter your email and password.")
      return
    }
    setLoading(true)
    try {
      await login(email, password)
      nav("/")
    } catch (err: unknown) {
      setError(authErrorMessage(err, "Sign-in failed — please try again."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-1/2 flex-col overflow-hidden bg-indigo-950 p-12 text-white lg:flex">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 to-slate-900" />
        <div className="relative z-10 flex h-full flex-col">
          <div className="mb-auto flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500">
              <BookOpen size={18} />
            </div>
            <span className="text-lg font-semibold">Study Companion</span>
          </div>
          <div className="flex flex-1 flex-col items-center justify-center gap-10">
            <KnowledgeGraphSVG />
            <div className="max-w-xs text-center">
              <h1 className="font-display mb-3 text-3xl font-semibold leading-snug">
                Turn your own study material into a measurable learning system.
              </h1>
              <p className="text-sm leading-relaxed text-indigo-300">
                Upload → Understand → Learn → Practice → Explain → Measure → Detect Weakness → Recommend → Improve
              </p>
            </div>
          </div>
          <div className="mt-auto flex gap-8 text-sm text-indigo-400">
            <div className="flex items-center gap-2"><Brain size={14} /> AI-grounded learning</div>
            <div className="flex items-center gap-2"><Network size={14} /> Evidence-based mastery</div>
          </div>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center bg-white p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="mb-1 text-2xl font-semibold text-slate-900">Welcome back</h2>
            <p className="text-sm text-slate-500">Sign in to continue learning</p>
          </div>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={15} className="shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@university.edu"
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700" htmlFor="password">Password</label>
                <button type="button" className="text-xs text-indigo-600 hover:underline">Forgot password?</button>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPw ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 pr-10 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  onClick={() => setShowPw((p) => !p)}
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-60"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : null}
              {loading ? "Signing in…" : "Sign in"}
              {!loading && <ArrowRight size={15} />}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Don&apos;t have an account?{" "}
            <Link to="/register" className="font-medium text-indigo-600 hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
