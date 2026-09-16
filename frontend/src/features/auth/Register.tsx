import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { BookOpen, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { authErrorMessage } from "@/lib/api-error"

export function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm) {
      setError("Passwords do not match.")
      return
    }
    setLoading(true)
    try {
      await register(form.email, form.password)
      nav("/")
    } catch (err: unknown) {
      setError(authErrorMessage(err, "Registration failed — please try again."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-1/2 flex-col overflow-hidden bg-indigo-950 p-12 text-white lg:flex">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 to-slate-900" />
        <div className="relative z-10 flex h-full flex-col">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500">
              <BookOpen size={18} />
            </div>
            <span className="text-lg font-semibold">Study Companion</span>
          </div>
          <div className="mx-auto flex max-w-xs flex-1 flex-col justify-center">
            <h1 className="font-display mb-4 text-3xl font-semibold leading-snug">
              A personal AI learning operating system.
            </h1>
            <ul className="space-y-3 text-sm text-indigo-300">
              {[
                "Upload your own study material",
                "AI-generated knowledge maps from your notes",
                "Evidence-based mastery tracking",
                "Detects confidence vs. correctness mismatches",
                "Personalized study recommendations",
              ].map((s, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center bg-white p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="mb-1 text-2xl font-semibold text-slate-900">Create your account</h2>
            <p className="text-sm text-slate-500">Start building your personal learning system</p>
          </div>

          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={onSubmit} className="space-y-4">
            {[
              { label: "Full name", key: "name", type: "text", placeholder: "Ada Lovelace" },
              { label: "Email address", key: "email", type: "email", placeholder: "you@university.edu" },
              { label: "Password", key: "password", type: "password", placeholder: "••••••••" },
              { label: "Confirm password", key: "confirm", type: "password", placeholder: "••••••••" },
            ].map((field) => (
              <div key={field.key}>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">{field.label}</label>
                <input
                  type={field.type}
                  required={field.key !== "name"}
                  minLength={field.key.includes("password") ? 8 : undefined}
                  placeholder={field.placeholder}
                  value={(form as Record<string, string>)[field.key]}
                  onChange={(e) => setForm((f) => ({ ...f, [field.key]: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-60"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-indigo-600 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
