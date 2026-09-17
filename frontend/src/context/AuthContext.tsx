import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import apiClient from "@/lib/axios"

export type User = {
  id: string
  email: string
  is_admin: boolean
  created_at: string
}

type AuthContextType = {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("access_token"))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  // On mount, if token exists, fetch /auth/me to hydrate user
  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    apiClient
      .get<User>("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        // expired/invalid -> clear
        localStorage.removeItem("access_token")
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [token])

  const login = async (email: string, password: string) => {
    const res = await apiClient.post<{ access_token: string; token_type: string }>("/auth/login", {
      email,
      password,
    })
    const newToken = res.data.access_token
    localStorage.setItem("access_token", newToken)
    setToken(newToken)
    // fetch user
    const me = await apiClient.get<User>("/auth/me", {
      headers: { Authorization: `Bearer ${newToken}` },
    })
    setUser(me.data)
    return me.data
  }

  const register = async (email: string, password: string) => {
    await apiClient.post("/auth/register", { email, password })
    // auto-login after register
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem("access_token")
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
