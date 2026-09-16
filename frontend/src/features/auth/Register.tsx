import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight, FileUp, MessagesSquare, Wand2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { apiError } from "@/lib/api-error"
import { Logo } from "@/components/ui"

const STEPS = [
  { icon: FileUp, title: "Upload", text: "Drop in your PDFs" },
  { icon: MessagesSquare, title: "Chat & quiz", text: "Study with your AI tutor" },
  { icon: Wand2, title: "Master", text: "Track mastery per concept" },
]

export function Register() {
  const { register } = useAuth()
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
      await register(email, password)
      nav("/")
    } catch (err: unknown) {
      setError(apiError(err).message ?? "Registration failed — email may already be taken")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-indigo-700 via-violet-700 to-fuchsia-700 p-10 text-white lg:flex">
        <div className="bg-dots absolute inset-0 opacity-20 [mask-image:radial-gradient(70%_60%_at_70%_25%,black,transparent)]" />
        <Link to="/" className="relative inline-flex w-fit items-center gap-2.5 rounded-2xl bg-white/10 px-3 py-2 backdrop-blur">
          <Logo compact />
          <span className="text-lg font-extrabold tracking-tight">StudyCompanion</span>
        </Link>
        <div className="relative">
          <h2 className="max-w-md text-4xl font-extrabold leading-tight tracking-tight">
            Turn your notes into <span className="text-amber-300">A&apos;s</span>.
          </h2>
          <div className="mt-8 space-y-4">
            {STEPS.map((s, i) => (
              <div key={s.title} className="flex items-center gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15 font-extrabold backdrop-blur">
                  {i + 1}
                </span>
                <div>
                  <p className="flex items-center gap-1.5 text-sm font-bold">
                    <s.icon className="h-4 w-4 text-amber-300" /> {s.title}
                  </p>
                  <p className="text-sm text-white/70">{s.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-white/60">Free to start · No credit card · Your data stays yours</p>
      </div>

      {/* Form panel */}
      <div className="bg-mesh flex flex-1 items-center justify-center px-4 py-12 sm:px-8">
        <div className="animate-fade-up w-full max-w-md">
          <Link to="/" className="lg:hidden">
            <Logo />
          </Link>
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight">Create your account</h1>
          <p className="mt-1.5 text-muted-foreground">One identity for all your study spaces.</p>
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
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-sm shadow-sm transition-all placeholder:text-muted-foreground/70 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-500/15"
                placeholder="At least 8 characters"
              />
            </div>
            {error && <p className="rounded-xl bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-sm font-bold text-white shadow-soft transition-all hover:shadow-lift hover:brightness-110 disabled:opacity-50"
            >
              {loading ? "Creating…" : <>Start studying free <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>
          <p className="mt-5 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-bold text-violet-700 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
