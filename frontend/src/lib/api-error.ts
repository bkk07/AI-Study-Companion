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
