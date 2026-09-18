import axios, { type AxiosRequestConfig } from "axios"
import { notifyUnauthorized } from "@/lib/auth-events"

/**
 * Centralized Axios client for the AI Study Companion frontend.
 * All API calls must go through this instance; do not hard-code URLs in components.
 *
 * - baseURL is derived from VITE_API_BASE_URL (host-resolvable, e.g. http://localhost:8000)
 *   with the versioned prefix appended. Falls back to localhost:8000 for local dev.
 * - JWT interceptor is added here (Phase 12 will attach Authorization header).
 */
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
const apiPrefix = import.meta.env.VITE_API_V1_PREFIX ?? "/api/v1"

// Ensure no double slash: baseURL = "http://localhost:8000/api/v1"
const baseURL = `${apiBaseUrl.replace(/\/$/, "")}${apiPrefix}`

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
})

// Attach JWT from localStorage (Phase 13). Token is stored under `access_token`.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token")
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url: string = error.config?.url ?? ""
      // Don't auto-redirect on auth endpoints themselves (login/register/me)
      if (!url.includes("/auth/login") && !url.includes("/auth/register")) {
        localStorage.removeItem("access_token")
        // SPA-safe: AuthProvider listens and does logout + router navigate.
        // Never window.location.href here — that hard-reloads the whole app.
        notifyUnauthorized()
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

// ---------------------------------------------------------------------------
// Tiny in-memory GET cache: every view fetches on mount, so tab switches and
// back-navigation re-request identical data. Cache GET responses for 30s and
// clear the whole cache on any mutation (POST/PUT/PATCH/DELETE), so writes
// are always followed by fresh reads. Live polling must opt out explicitly:
//   apiClient.get(url, { noCache: true })
declare module "axios" {
  export interface AxiosRequestConfig {
    noCache?: boolean
  }
}

const GET_CACHE_TTL_MS = 30_000

type CacheEntry = { expiresAt: number; data: unknown; status: number }
const getCache = new Map<string, CacheEntry>()

function cacheKey(config: AxiosRequestConfig): string {
  return `${config.baseURL ?? ""}::${config.url ?? ""}::${JSON.stringify(config.params ?? null)}`
}

const defaultAdapter = axios.getAdapter("xhr")

apiClient.defaults.adapter = async (config) => {
  const method = (config.method ?? "get").toLowerCase()
  if (method === "get" && !config.noCache) {
    const hit = getCache.get(cacheKey(config))
    if (hit && hit.expiresAt > Date.now()) {
      return { data: hit.data, status: hit.status, statusText: "OK", headers: {}, config }
    }
  }
  const response = await defaultAdapter(config)
  if (method === "get") {
    if (!config.noCache) {
      getCache.set(cacheKey(config), {
        expiresAt: Date.now() + GET_CACHE_TTL_MS,
        data: response.data,
        status: response.status,
      })
    }
  } else {
    // Any write invalidates cached reads — cheap and always safe.
    getCache.clear()
  }
  return response
}
