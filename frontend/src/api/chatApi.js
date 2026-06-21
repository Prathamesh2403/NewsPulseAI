/**
 * Chat API — SSE streaming client.
 *
 * IMPORTANT: This module must be the ONLY consumer of the response stream.
 * The onChunk/onCitations/onDone callbacks are called exactly once per event.
 * onDone is tracked with a flag so it never fires twice.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export function sendChatMessage(query, chatHistory = [], { onChunk, onCitations, onDone, onError }) {
  const controller = new AbortController()
  let doneFired = false

  const fireDone = () => {
    if (doneFired) return
    doneFired = true
    onDone?.()
  }

  ;(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, chat_history: chatHistory }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => 'Unknown error')
        onError?.(`Server error (${res.status}): ${text}`)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // keep incomplete last line

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const dataStr = line.slice(5).trim()
            if (!dataStr) continue
            try {
              const data = JSON.parse(dataStr)
              switch (currentEvent) {
                case 'token':
                  onChunk?.(data.text ?? '')
                  break
                case 'citations':
                  onCitations?.(data.citations ?? [])
                  break
                case 'done':
                  fireDone()
                  break
                case 'error':
                  onError?.(data.error || 'Unknown error')
                  break
              }
            } catch (e) {
              console.warn('SSE parse error:', e, dataStr)
            }
          }
        }
      }

      // Stream reader finished — ensure done fires
      fireDone()
    } catch (err) {
      if (err.name === 'AbortError') return
      onError?.(err.message || 'Network error. Is the backend running?')
    }
  })()

  return () => controller.abort()
}
