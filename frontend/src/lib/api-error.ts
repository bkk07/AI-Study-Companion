/**
 * Single client-side reader for API failures (Phase 48).
 * All components must extract error info through this helper — never by
 * reaching into `response.data` shapes directly.
 *
 * The API emits one envelope: `{ error: { code, message, details? } }`.
 * A legacy `detail` fallback is kept for resilience against non-normalized
 * responses (proxies, network failures).
 */
export type ApiErrorInfo = {
  status?: number
  message?: string
}

export function apiError(e: unknown): ApiErrorInfo {
  const response = (e as { response?: { status?: number; data?: unknown } })?.response
  const data = response?.data as
    | { error?: { message?: string }; detail?: string }
    | undefined
  return {
    status: response?.status,
    message: data?.error?.message ?? data?.detail,
  }
}

/**
 * Honest auth-form messaging: show the server's message when there is one,
 * admit connectivity problems when there is no response at all, and otherwise
 * stay neutral — never blame the email/password without the server saying so.
 */
export function authErrorMessage(e: unknown, fallback: string): string {
  const info = apiError(e)
  if (info.message) return info.message
  const hasResponse = (e as { response?: unknown })?.response != null
  if (!hasResponse) return "Can't reach the server — check your connection and try again."
  return fallback
}
