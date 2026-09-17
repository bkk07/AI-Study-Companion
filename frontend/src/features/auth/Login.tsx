import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { authErrorMessage } from "@/lib/api-error"
import { AuthSidePanel } from "@/features/auth/AuthSidePanel"

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
      const u = await login(email, password)
      nav(u.is_admin ? "/admin" : "/")
    } catch (err: unknown) {
      setError(authErrorMessage(err, "Sign-in failed — please try again."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-100">
      <AuthSidePanel
        image="https://images.unsplash.com/photo-1507842217343-583bb7270b66?q=80&w=1600&auto=format&fit=crop"
        imageAlt="Grand university library hall with tall bookshelves"
        title="Turn your own study material into a measurable learning system."
        subtitle="Your uploads in. Grounded answers, measured mastery, and what's-next guidance out."
        slides={[
          {
            title: "Grounded answers",
            text: "Every tutor reply cites your uploads — or honestly says the material doesn't cover it.",
          },
          {
            title: "Evidence-based mastery",
            text: "Quizzes, flashcards, and explanations banked as signal per concept.",
          },
          {
            title: "Weakness radar",
            text: "Confidence vs. correctness mismatches surfaced before exam day.",
          },
        ]}
      />

      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-8">
            <h2 className="mb-1 text-2xl font-semibold tracking-tight text-slate-900">Welcome back</h2>
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
