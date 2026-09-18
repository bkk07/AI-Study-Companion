// Module-level 401 signal — lets the axios interceptor (outside React) tell
// AuthProvider (inside React) that the session died, without window.location
// hard-reloads. AuthProvider subscribes once and handles logout + SPA navigate.
type Handler = () => void

const handlers = new Set<Handler>()

export function subscribeUnauthorized(handler: Handler): () => void {
  handlers.add(handler)
  return () => {
    handlers.delete(handler)
  }
}

export function notifyUnauthorized(): void {
  handlers.forEach((handler) => {
    try {
      handler()
    } catch {
      // one bad subscriber must never break the request chain
    }
  })
}
