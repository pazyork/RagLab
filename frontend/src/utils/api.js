/**
 * Unified fetch wrapper with proper error handling.
 *
 * - Robustly reads error bodies (handles empty body, interrupted streams)
 * - Distinguishes HTTP status codes for better error messages
 * - Returns parsed JSON for successful responses
 */
export async function fetchJson(url, options = {}) {
  const res = await fetch(url, options)

  if (!res.ok) {
    // Try to read error body; handle potential read failures
    let detail = ''
    try {
      const text = await res.text()
      // FastAPI wraps errors in {"detail": "..."}
      try {
        const json = JSON.parse(text)
        detail = json.detail || text
      } catch {
        detail = text
      }
    } catch {
      // Body read failed (interrupted stream etc.)
      detail = ''
    }

    const statusLabel = {
      400: 'Bad request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Not found',
      422: 'Validation error',
      500: 'Server error',
      502: 'Service unavailable',
      503: 'Service unavailable',
    }[res.status] || `HTTP ${res.status}`

    const message = detail ? `${statusLabel}: ${detail}` : statusLabel
    throw new Error(message)
  }

  return res.json()
}
