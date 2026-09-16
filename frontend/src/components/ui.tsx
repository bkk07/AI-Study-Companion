import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react"
import { AlertCircle, Loader2, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

/* ---------- Button ---------- */

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "destructive"
type ButtonSize = "sm" | "md" | "lg"

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-soft hover:shadow-lift hover:brightness-110 active:brightness-95",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/70",
  outline: "border border-input bg-card hover:border-violet-300 hover:bg-violet-50/60",
  ghost: "hover:bg-muted",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
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
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-semibold transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
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
    <div style={style} className={cn("rounded-2xl border bg-card shadow-soft", className)}>
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
  "w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-sm shadow-sm transition-all placeholder:text-muted-foreground/70 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-500/15 disabled:opacity-50"

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
    <div className="flex items-center gap-2.5 py-8 text-sm text-muted-foreground">
      <Spinner className="h-5 w-5 text-violet-500" />
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
    <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
      <p className="flex items-start gap-2 text-sm font-medium text-rose-700">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 text-sm font-semibold text-violet-700 hover:underline"
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
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-violet-200 bg-violet-50/50 px-6 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 text-white shadow-soft">
        {icon}
      </div>
      <p className="mt-3 font-semibold">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
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
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-violet-600">{eyebrow}</p>
        )}
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight">{title}</h1>
        {description && <p className="mt-1.5 max-w-xl text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

/* ---------- Brand ---------- */

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 via-purple-600 to-fuchsia-500 text-white shadow-soft">
        <Sparkles className="h-5 w-5" />
      </span>
      {!compact && (
        <span className="text-lg font-extrabold tracking-tight">
          Study<span className="text-gradient">Companion</span>
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
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-sm font-bold text-white",
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
  barClass = "from-violet-500 to-fuchsia-500",
}: {
  value: number | null
  className?: string
  barClass?: string
}) {
  if (value === null) {
    return (
      <div className={cn("h-2.5 rounded-full bg-muted", className)}>
        <div className="h-2.5 w-1/4 rounded-full bg-muted-foreground/20" />
      </div>
    )
  }
  const pct = Math.min(100, Math.max(0, value))
  return (
    <div className={cn("h-2.5 overflow-hidden rounded-full bg-violet-100", className)}>
      <div
        className={cn("h-full rounded-full bg-gradient-to-r transition-all duration-500", barClass)}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
