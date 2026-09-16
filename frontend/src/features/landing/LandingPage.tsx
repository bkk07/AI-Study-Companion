import { Link } from "react-router-dom"
import {
  ArrowRight,
  BadgeCheck,
  BrainCircuit,
  FileUp,
  Gamepad2,
  LineChart,
  MessagesSquare,
  Quote,
  Sparkles,
  UploadCloud,
} from "lucide-react"
import { AppShell } from "@/components/AppShell"
import { Card } from "@/components/ui"

const FEATURES = [
  {
    icon: MessagesSquare,
    title: "AI tutor that cites sources",
    text: "Ask anything about your materials. Every answer is grounded in your uploads — with page citations, never hallucinations.",
  },
  {
    icon: BrainCircuit,
    title: "Adaptive quizzes",
    text: "MCQs generated from your PDFs, auto-tuned to your weakest concepts and matched to your level.",
  },
  {
    icon: BrainCircuit,
    title: "Mastery tracking",
    text: "Recognition vs. applied understanding, per concept — so you know what you really know, not just what feels familiar.",
  },
  {
    icon: LineChart,
    title: "Growth over time",
    text: "Watch your mastery curve climb with every quiz, explanation, and review session.",
  },
  {
    icon: Gamepad2,
    title: "Explain-it-back challenges",
    text: "Teach it back to prove applied understanding — the fastest way to lock knowledge in.",
  },
  {
    icon: BadgeCheck,
    title: "Smart recommendations",
    text: "Always know exactly what to do next: quiz, review, explain, or ask — picked for your gaps.",
  },
]

const STEPS = [
  {
    icon: UploadCloud,
    title: "Upload your PDFs",
    text: "Drop in lecture notes, textbooks, or slides. We extract, chunk, and map every concept.",
  },
  {
    icon: FileUp,
    title: "Get your learning map",
    text: "A clean Topic → Subtopic → Concept outline appears, ready to study from.",
  },
  {
    icon: Sparkles,
    title: "Study with AI",
    text: "Chat, quiz, explain back — while mastery, mismatches, and growth update live.",
  },
]

export function LandingPage() {
  return (
    <AppShell>
      <section className="relative overflow-hidden bg-slate-50">
        <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-24">
          <div className="inline-flex">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-100 bg-indigo-50 px-3.5 py-1.5 text-xs font-medium text-indigo-700">
              <Sparkles size={14} />
              Your project-scoped AI study partner
            </span>
          </div>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-5xl">
            Learning that adapts to you
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-500">
            Stop fighting your notes. Upload your course materials and get a personal tutor,
            adaptive quizzes, and mastery tracking — all grounded in what your professor actually gave you.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-7 py-2.5 text-base font-medium text-white hover:bg-indigo-700"
            >
              Try for free <ArrowRight size={16} />
            </Link>
            <Link
              to="/login"
              className="rounded-lg border border-slate-200 bg-white px-7 py-2.5 text-base font-medium text-slate-700 hover:bg-slate-50"
            >
              Sign in
            </Link>
          </div>

          <div className="relative mx-auto mt-14 max-w-3xl">
            <Card className="p-5 text-left sm:p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
                  <MessagesSquare size={20} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Tutor</p>
                  <p className="text-xs text-slate-500">Grounded in “Linear Algebra Ch. 3.pdf”</p>
                </div>
                <span className="ml-auto rounded-full border border-green-200 bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">Supported</span>
              </div>
              <div className="ml-auto mt-4 max-w-[80%] rounded-xl bg-indigo-600 px-4 py-2.5 text-sm text-white">
                Why does the slope formula work?
              </div>
              <div className="mt-2 max-w-[90%] rounded-xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700">
                Slope measures <strong>rise over run</strong> — how much y changes for each step in x [1].
                That&apos;s why parallel lines share the same slope [1, p. 42].
              </div>
            </Card>
          </div>
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-8 text-center sm:grid-cols-4 sm:px-6">
          {[
            ["6 study tools", "tutor · quizzes · maps · more"],
            ["2 mastery tracks", "recognition + applied"],
            ["100% grounded", "every answer cites uploads"],
            ["Private by design", "scoped per project"],
          ].map(([big, small]) => (
            <div key={big}>
              <p className="font-mono-data text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">{big}</p>
              <p className="mt-0.5 text-xs text-slate-500 sm:text-sm">{small}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl bg-slate-50 px-4 py-16 sm:px-6 sm:py-20">
        <p className="text-center text-xs font-semibold uppercase tracking-widest text-slate-400">Features</p>
        <h2 className="mx-auto mt-2 max-w-2xl text-center text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          Everything you need to really learn
        </h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title} className="group p-6 transition-all hover:border-slate-300 hover:shadow-sm">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <f.icon size={18} />
              </span>
              <h3 className="mt-4 text-base font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{f.text}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <p className="text-center text-xs font-semibold uppercase tracking-widest text-slate-400">How it works</p>
          <h2 className="mx-auto mt-2 max-w-2xl text-center text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            Studying in seconds, not hours
          </h2>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <div key={s.title} className="relative rounded-xl border border-slate-200 bg-white p-6">
                <span className="absolute right-5 top-4 text-5xl font-bold text-slate-100">{i + 1}</span>
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <s.icon size={18} />
                </span>
                <h3 className="mt-4 text-base font-semibold text-slate-900">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{s.text}</p>
              </div>
            ))}
          </div>
          <div className="mt-10 text-center">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-8 py-2.5 text-base font-medium text-white hover:bg-indigo-700"
            >
              Get started free <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl bg-slate-50 px-4 py-16 text-center sm:px-6">
        <Quote className="mx-auto h-8 w-8 text-slate-300" />
        <blockquote className="mt-4 text-xl font-semibold leading-relaxed tracking-tight text-slate-900 sm:text-2xl">
          “I stopped re-reading my notes and started actually understanding them. The tutor shows me exactly
          where every answer comes from.”
        </blockquote>
        <p className="mt-4 text-sm text-slate-500">A very focused student · Probably you, next semester</p>
      </section>
    </AppShell>
  )
}
