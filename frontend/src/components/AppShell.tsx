import { Link, NavLink, useNavigate } from "react-router-dom"
import { LayoutDashboard, LogOut, ShieldCheck, Sparkles } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { Avatar, Logo } from "@/components/ui"
import { cn } from "@/lib/utils"

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    "inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-semibold transition-colors",
    isActive ? "bg-violet-100 text-violet-800" : "text-muted-foreground hover:bg-muted hover:text-foreground",
  )
}

export function AppShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const { user, token, logout } = useAuth()
  const nav = useNavigate()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-white/40 bg-white/75 backdrop-blur-xl">
        <div className={cn("mx-auto flex h-16 items-center justify-between gap-4 px-4 sm:px-6", wide ? "max-w-7xl" : "max-w-6xl")}>
          <Link to={token ? "/spaces" : "/"} aria-label="Home">
            <Logo />
          </Link>
          <nav className="flex items-center gap-1">
            {token ? (
              <>
                <NavLink to="/spaces" className={navClass}>
                  <LayoutDashboard className="h-4 w-4" />
                  <span className="hidden sm:inline">My spaces</span>
                  <span className="sm:hidden">Spaces</span>
                </NavLink>
                {user?.is_admin && (
                  <NavLink to="/admin" className={navClass}>
                    <ShieldCheck className="h-4 w-4" />
                    Admin
                  </NavLink>
                )}
                <span className="mx-1 hidden h-6 w-px bg-border sm:block" />
                {user && (
                  <span className="hidden items-center gap-2 md:inline-flex">
                    <Avatar email={user.email} className="h-8 w-8 text-xs" />
                    <span className="max-w-44 truncate text-sm font-medium">{user.email}</span>
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => {
                    logout()
                    nav("/login")
                  }}
                  className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Sign out</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="rounded-xl px-4 py-2 text-sm font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-soft transition-all hover:shadow-lift hover:brightness-110"
                >
                  <Sparkles className="h-4 w-4" />
                  Start free
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t bg-white/60">
        <div className={cn("mx-auto flex flex-col items-center justify-between gap-2 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:px-6", wide ? "max-w-7xl" : "max-w-6xl")}>
          <span className="inline-flex items-center gap-1.5">
            <Logo compact />
            <span className="font-semibold text-foreground">StudyCompanion</span> — learn anything faster.
          </span>
          <span>Your materials stay private to your projects · Answers cite your uploads</span>
        </div>
      </footer>
    </div>
  )
}
