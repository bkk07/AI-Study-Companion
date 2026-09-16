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
  Wand2,
} from "lucide-react"
import { AppShell } from "@/components/AppShell"
import { Badge, Button, Card } from "@/components/ui"

const FEATURES = [
  {
    icon: MessagesSquare,
    tint: "from-violet-500 to-purple-600",
    title: "AI tutor that cites sources",
    text: "Ask anything about your materials. Every answer is grounded in your uploads — with page citations, never hallucinations.",
  },
  {
    icon: Wand2,
    tint: "from-fuchsia-500 to-pink-500",
    title: "Adaptive quizzes",
    text: "MCQs generated from your PDFs, auto-tuned to your weakest concepts and matched to your level.",
  },
  {
    icon: BrainCircuit,
    tint: "from-indigo-500 to-blue-500",
    title: "Mastery tracking",
    text: "Recognition vs. applied understanding, per concept — so you know what you really know, not just what feels familiar.",
  },
  {
    icon: LineChart,
    tint: "from-emerald-500 to-teal-500",
    title: "Growth over time",
    text: "Watch your mastery curve climb with every quiz, explanation, and review session.",
  },
  {
    icon: Gamepad2,
    tint: "from-amber-500 to-orange-500",
    title: "Explain-it-back challenges",
    text: "Teach it back to prove applied understanding — the fastest way to lock knowledge in.",
  },
  {
    icon: BadgeCheck,
    tint: "from-sky-500 to-cyan-500",
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
      {/* ---------- Hero ---------- */}
      <section className="bg-mesh relative overflow-hidden">
        <div className="bg-dots pointer-events-none absolute inset-0 opacity-40 [mask-image:radial-gradient(60%_60%_at_50%_30%,black,transparent)]" />
        <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-24">
          <div className="animate-fade-up inline-flex">
            <Badge tint="violet" className="px-3.5 py-1.5 text-xs shadow-soft">
              <Sparkles className="h-3.5 w-3.5" />
              Your project-scoped AI study partner
            </Badge>
          </div>
          <h1
            className="animate-fade-up stagger mx-auto mt-6 max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl"
            style={{ "--d": "90ms" } as React.CSSProperties}
          >
            Learning that <span className="text-gradient">adapts to you</span>
          </h1>
          <p
            className="animate-fade-up stagger mx-auto mt-5 max-w-2xl text-lg text-muted-foreground"
            style={{ "--d": "180ms" } as React.CSSProperties}
          >
            Stop fighting your notes. Upload your course materials and get a personal tutor,
            adaptive quizzes, and mastery tracking — all grounded in what your professor actually gave you.
          </p>
          <div
            className="animate-fade-up stagger mt-8 flex flex-wrap items-center justify-center gap-3"
            style={{ "--d": "270ms" } as React.CSSProperties}
          >
            <Link to="/register">
              <Button size="lg" className="px-7">
                Try for free <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline" className="px-7">
                Sign in
              </Button>
            </Link>
          </div>

          {/* Hero preview card */}
          <div
            className="animate-fade-up stagger relative mx-auto mt-14 max-w-3xl"
            style={{ "--d": "360ms" } as React.CSSProperties}
          >
            <div className="animate-float-slow absolute -left-4 -top-6 hidden rotate-[-8deg] rounded-2xl border bg-card px-4 py-3 text-left shadow-lift sm:block">
              <p className="text-xs font-bold text-violet-700">Recognition 92%</p>
              <div className="mt-1.5 h-2 w-36 overflow-hidden rounded-full bg-violet-100">
                <div className="h-full w-[92%] rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500" />
              </div>
            </div>
            <div className="animate-float-slow absolute -right-4 top-10 hidden rotate-[6deg] rounded-2xl border bg-card px-4 py-3 text-left shadow-lift sm:block" style={{ animationDelay: "1.2s" }}>
              <p className="text-xs font-bold text-emerald-700">Quiz: 4/5 correct ✓</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">Slope · Applied +6.2</p>
            </div>
            <Card className="p-5 text-left shadow-lift sm:p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white">
                  <MessagesSquare className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-sm font-bold">Tutor</p>
                  <p className="text-xs text-muted-foreground">Grounded in “Linear Algebra Ch. 3.pdf”</p>
                </div>
                <Badge tint="emerald" className="ml-auto">Supported</Badge>
              </div>
              <div className="ml-auto mt-4 max-w-[80%] rounded-2xl rounded-br-md bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-2.5 text-sm text-white">
                Why does the slope formula work?
              </div>
              <div className="mt-2 max-w-[90%] rounded-2xl rounded-bl-md border bg-muted/60 px-4 py-2.5 text-sm">
                Slope measures <strong>rise over run</strong> — how much y changes for each step in x [1].
                That&apos;s why parallel lines share the same slope [1, p. 42].
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* ---------- Stats band ---------- */}
      <section className="border-y bg-white/70">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-8 text-center sm:grid-cols-4 sm:px-6">
          {[
            ["6 study tools", "tutor · quizzes · maps · more"],
            ["2 mastery tracks", "recognition + applied"],
            ["100% grounded", "every answer cites uploads"],
            ["Private by design", "scoped per project"],
          ].map(([big, small]) => (
            <div key={big}>
              <p className="text-xl font-extrabold tracking-tight sm:text-2xl">{big}</p>
              <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">{small}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- Features ---------- */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <p className="text-center text-xs font-bold uppercase tracking-[0.16em] text-violet-600">Features</p>
        <h2 className="mx-auto mt-2 max-w-2xl text-center text-3xl font-extrabold tracking-tight sm:text-4xl">
          Everything you need to <span className="text-gradient">really learn</span>
        </h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Card
              key={f.title}
              className="animate-fade-up stagger group p-6 transition-all hover:-translate-y-1 hover:shadow-lift"
              style={{ "--d": `${i * 70}ms` } as React.CSSProperties}
            >
              <span className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-soft ${f.tint}`}>
                <f.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 font-bold">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{f.text}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="border-y bg-gradient-to-b from-violet-50/80 to-white">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <p className="text-center text-xs font-bold uppercase tracking-[0.16em] text-violet-600">How it works</p>
          <h2 className="mx-auto mt-2 max-w-2xl text-center text-3xl font-extrabold tracking-tight sm:text-4xl">
            Studying in seconds, not hours
          </h2>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <div key={s.title} className="relative rounded-2xl border bg-card p-6 shadow-soft">
                <span className="absolute right-5 top-4 text-5xl font-extrabold text-violet-100">{i + 1}</span>
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                  <s.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 font-bold">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{s.text}</p>
              </div>
            ))}
          </div>
          <div className="mt-10 text-center">
            <Link to="/register">
              <Button size="lg" className="px-8">
                Get started free <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ---------- Quote ---------- */}
      <section className="mx-auto max-w-4xl px-4 py-16 text-center sm:px-6">
        <Quote className="mx-auto h-8 w-8 text-violet-300" />
        <blockquote className="mt-4 text-xl font-semibold leading-relaxed tracking-tight sm:text-2xl">
          “I stopped re-reading my notes and started <span className="text-gradient">actually understanding them</span>.
          The tutor shows me exactly where every answer comes from.”
        </blockquote>
        <p className="mt-4 text-sm text-muted-foreground">A very focused student · Probably you, next semester</p>
      </section>
    </AppShell>
  )
}
