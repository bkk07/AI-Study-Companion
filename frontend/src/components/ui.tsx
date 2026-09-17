import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react"
import { AlertCircle, Loader2, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

/* ---------- Button ---------- */

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "destructive" | "danger"
type ButtonSize = "sm" | "md" | "lg"

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700 active:bg-indigo-700",
  secondary: "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50",
  outline: "border border-input bg-card hover:border-indigo-300 hover:bg-indigo-50/60",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-800",
  destructive: "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100",
  danger: "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100",
}

const buttonSizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    />
  )
}

/* ---------- Card ---------- */

export function Card({
  className,
  style,
  children,
}: {
  className?: string
  style?: React.CSSProperties
  children: ReactNode
}) {
  return (
    <div style={style} className={cn("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {children}
    </div>
  )
}

/* ---------- Badge ---------- */

type BadgeTint = "violet" | "amber" | "emerald" | "sky" | "rose" | "muted"

const badgeTints: Record<BadgeTint, string> = {
  violet: "bg-violet-100 text-violet-700 ring-violet-200",
  amber: "bg-amber-100 text-amber-800 ring-amber-200",
  emerald: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  sky: "bg-sky-100 text-sky-700 ring-sky-200",
  rose: "bg-rose-100 text-rose-700 ring-rose-200",
  muted: "bg-muted text-muted-foreground ring-border",
}

export function Badge({
  tint = "violet",
  className,
  children,
}: {
  tint?: BadgeTint
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset",
        badgeTints[tint],
        className,
      )}
    >
      {children}
    </span>
  )
}

/* ---------- Inputs ---------- */

const fieldClass =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:opacity-50"

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(fieldClass, className)} {...props} />
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(fieldClass, "pr-8", className)} {...props}>
      {children}
    </select>
  )
}

/* ---------- Feedback states ---------- */

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-4 w-4 animate-spin", className)} aria-label="Loading" />
}

export function LoadingState({ text = "Loading…" }: { text?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-8 text-sm text-slate-500">
      <Spinner className="h-5 w-5 text-indigo-500" />
      {text}
    </div>
  )
}

export function ErrorBox({
  message,
  onRetry,
  retryLabel = "Try again",
}: {
  message: string
  onRetry?: () => void
  retryLabel?: string
}) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4">
      <p className="flex items-start gap-2 text-sm font-medium text-red-700">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 text-sm font-semibold text-indigo-600 hover:underline"
        >
          {retryLabel}
        </button>
      )}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon: ReactNode
  title: string
  hint?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-8 py-20 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-400">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
      {hint && <p className="mt-1 max-w-xs text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

/* ---------- Page header ---------- */

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: ReactNode
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="mb-1 text-xs uppercase tracking-wider text-slate-400">{eyebrow}</p>
        )}
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

/* ---------- Brand ---------- */

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white">
        <Sparkles className="h-3.5 w-3.5" />
      </span>
      {!compact && (
        <span className="text-sm font-semibold text-slate-900">
          Study Companion
        </span>
      )}
    </span>
  )
}

export function Avatar({ email, className }: { email: string; className?: string }) {
  const initial = (email.trim()[0] ?? "?").toUpperCase()
  return (
    <span
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700",
        className,
      )}
      title={email}
    >
      {initial}
    </span>
  )
}

/* ---------- Progress ---------- */

export function ProgressBar({
  value,
  className,
  barClass = "from-indigo-500 to-indigo-600",
}: {
  value: number | null
  className?: string
  barClass?: string
}) {
  if (value === null) {
    return (
      <div className={cn("h-2.5 rounded-full bg-slate-100", className)}>
        <div className="h-2.5 w-1/4 rounded-full bg-slate-200" />
      </div>
    )
  }
  const pct = Math.min(100, Math.max(0, value))
  return (
    <div className={cn("h-2.5 overflow-hidden rounded-full bg-slate-100", className)}>
      <div
        className={cn("h-full rounded-full bg-gradient-to-r transition-all duration-500", barClass)}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

/* ---------- Figma design system (adapted, real-data ready) ---------- */

export type MasteryLevel = "mastered" | "strong" | "developing" | "weak" | "unassessed"

/** Numeric fallback bands — mirrors backend mastery_levels (34 / 66 / 85). */
export function masteryLevelFor(value: number | null): MasteryLevel {
  if (value === null) return "unassessed"
  if (value >= 85) return "mastered"
  if (value > 66) return "strong"
  if (value >= 34) return "developing"
  return "weak"
}

/** Prefer the API status string; fall back to numeric bands when unknown. */
export function levelForStatus(status: string | null, value: number | null): MasteryLevel {
  if (status === "Mastered") return "mastered"
  if (status === "Strong") return "strong"
  if (status === "Developing") return "developing"
  if (status === "Needs Practice") return "weak"
  if (status === "Not Started") return "unassessed"
  return masteryLevelFor(value)
}

export function MasteryBadge({ level, size = "sm" }: { level: MasteryLevel; size?: "sm" | "md" }) {
  const labels: Record<MasteryLevel, string> = {
    mastered: "Mastered",
    strong: "Strong",
    developing: "Developing",
    weak: "Weak",
    unassessed: "Not Assessed",
  }
  const cls =
    size === "sm"
      ? "text-xs px-2 py-0.5 rounded-full font-medium"
      : "text-sm px-3 py-1 rounded-full font-medium"
  return <span className={`${cls} badge-${level}`}>{labels[level]}</span>
}

export function MasteryDot({ level }: { level: MasteryLevel }) {
  const colors: Record<MasteryLevel, string> = {
    mastered: "bg-green-500",
    strong: "bg-sky-500",
    developing: "bg-amber-500",
    weak: "bg-red-500",
    unassessed: "bg-slate-300",
  }
  return <span className={`inline-block h-2 w-2 rounded-full ${colors[level]} shrink-0`} />
}

export function MasteryBar({ value, level, label }: { value: number; level: MasteryLevel; label: string }) {
  const colors: Record<MasteryLevel, string> = {
    mastered: "bg-green-500",
    strong: "bg-sky-500",
    developing: "bg-amber-400",
    weak: "bg-red-400",
    unassessed: "bg-slate-300",
  }
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-600">{label}</span>
        <span className="font-mono-data text-sm font-semibold text-slate-800">{value}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${colors[level]}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

export function StatCard({
  label,
  value,
  sub,
  icon,
  accent = "slate",
  onClick,
}: {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
  accent?: "indigo" | "green" | "amber" | "red" | "slate"
  onClick?: () => void
}) {
  const accentBg: Record<string, string> = {
    indigo: "bg-indigo-50",
    green: "bg-green-50",
    amber: "bg-amber-50",
    red: "bg-red-50",
    slate: "bg-slate-50",
  }
  const accentIcon: Record<string, string> = {
    indigo: "text-indigo-600",
    green: "text-green-600",
    amber: "text-amber-600",
    red: "text-red-600",
    slate: "text-slate-600",
  }
  return (
    <div
      className={`space-y-3 rounded-xl border border-slate-100 bg-white p-5 ${onClick ? "cursor-pointer transition-all hover:border-slate-200 hover:shadow-sm" : ""}`}
      onClick={onClick}
    >
      {icon && (
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${accentBg[accent]} ${accentIcon[accent]}`}>
          {icon}
        </div>
      )}
      <div>
        <div className="font-mono-data text-2xl font-bold text-slate-900">{value}</div>
        <div className="mt-0.5 text-sm text-slate-500">{label}</div>
        {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
      </div>
    </div>
  )
}

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

export function Divider() {
  return <div className="my-6 border-t border-slate-100" />
}

export function Tag({ children, color = "slate" }: { children: ReactNode; color?: "indigo" | "green" | "amber" | "red" | "slate" }) {
  const colors: Record<string, string> = {
    indigo: "bg-indigo-50 text-indigo-700 border-indigo-100",
    green: "bg-green-50 text-green-700 border-green-100",
    amber: "bg-amber-50 text-amber-700 border-amber-100",
    red: "bg-red-50 text-red-700 border-red-100",
    slate: "bg-slate-50 text-slate-600 border-slate-200",
  }
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${colors[color]}`}>
      {children}
    </span>
  )
}
