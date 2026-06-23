import { useState, useEffect } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

/**
 * useApiHealth — pings the backend on app load to detect Render cold starts.
 *
 * Render Free Tier spins down after 15 min of inactivity. The first request
 * after spin-down takes 30–50 seconds. This hook detects that state and
 * exposes it so the UI can show a friendly "waking up" banner.
 *
 * Behaviour:
 *  - Immediately fires a health check to GET /
 *  - If the first check fails, sets isWaking=true (banner appears)
 *  - Retries every 5 seconds, up to 10 times (~50 seconds total)
 *  - Sets isReady=true once the server responds OK, or after all retries exhausted
 */
export function useApiHealth() {
  const [isWaking, setIsWaking] = useState(false)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    let attempts = 0
    const maxAttempts = 10  // try for ~50 seconds

    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/`, {
          signal: AbortSignal.timeout(6000),
        })
        if (res.ok) {
          setIsReady(true)
          setIsWaking(false)
          return
        }
      } catch {
        // server still waking up — fall through to retry logic
      }

      attempts++
      if (attempts === 1) {
        // Only show the banner after the first failed attempt
        // so fast responses don't flash the banner at all.
        setIsWaking(true)
      }

      if (attempts < maxAttempts) {
        setTimeout(checkHealth, 5000)  // retry every 5 seconds
      } else {
        // Give up waiting — let the user try anyway
        setIsReady(true)
        setIsWaking(false)
      }
    }

    checkHealth()
  }, [])

  return { isWaking, isReady }
}
