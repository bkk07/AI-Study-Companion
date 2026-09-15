import axios from "axios"

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

// Request interceptor placeholder — auth header is attached in Phase 12/13.
// Keeping the interceptor here centralizes token handling.
apiClient.interceptors.request.use((config) => {
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error)
  }
)

export default apiClient
