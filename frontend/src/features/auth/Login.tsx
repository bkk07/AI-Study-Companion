import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight, BadgeCheck, BrainCircuit, MessagesSquare } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { authErrorMessage } from "@/lib/api-error"
import { Logo } from "@/components/ui"

const PERKS = [
  { icon: MessagesSquare, text: "A tutor that cites your uploads" },
  { icon: BrainCircuit, text: "Mastery tracking per concept" },
  { icon: BadgeCheck, text: "Private to your projects" },
]

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
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
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-violet-700 via-purple-700 to-fuchsia-700 p-10 text-white lg:flex">
        <div className="bg-dots absolute inset-0 opacity-20 [mask-image:radial-gradient(70%_60%_at_30%_20%,black,transparent)]" />
        <Link to="/" className="relative inline-flex w-fit items-center gap-2.5 rounded-2xl bg-white/10 px-3 py-2 backdrop-blur">
          <Logo compact />
          <span className="text-lg font-extrabold tracking-tight">StudyCompanion</span>
        </Link>
        <div className="relative">
          <h2 className="max-w-md text-4xl font-extrabold leading-tight tracking-tight">
            Pick up exactly where you left off.
          </h2>
          <ul className="mt-8 space-y-3">
            {PERKS.map((p) => (
              <li key={p.text} className="flex items-center gap-3 text-sm font-medium text-white/90">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15 backdrop-blur">
                  <p.icon className="h-4 w-4" />
                </span>
                {p.text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/60">Grounded answers · Adaptive quizzes · Mastery curves</p>
      </div>

      {/* Form panel */}
      <div className="bg-mesh flex flex-1 items-center justify-center px-4 py-12 sm:px-8">
        <div className="animate-fade-up w-full max-w-md">
          <Link to="/" className="lg:hidden">
            <Logo />
          </Link>
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight">Welcome back</h1>
          <p className="mt-1.5 text-muted-foreground">Sign in to continue studying.</p>
          <form onSubmit={onSubmit} className="mt-7 space-y-4 rounded-2xl border bg-card p-6 shadow-soft sm:p-7">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-sm shadow-sm transition-all placeholder:text-muted-foreground/70 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-500/15"
                placeholder="you@example.com"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-sm shadow-sm transition-all placeholder:text-muted-foreground/70 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-500/15"
                placeholder="••••••••"
              />
            </div>
            {error && <p className="rounded-xl bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-sm font-bold text-white shadow-soft transition-all hover:shadow-lift hover:brightness-110 disabled:opacity-50"
            >
              {loading ? "Signing in…" : <>Sign in <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>
          <p className="mt-5 text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link to="/register" className="font-bold text-violet-700 hover:underline">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
