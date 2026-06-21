import { useState, useCallback, useRef, useEffect } from 'react'
import { sendChatMessage } from '../api/chatApi'
import { 
  getActiveSessionId, 
  getSession, 
  saveSession, 
  setActiveSession, 
  createNewSession 
} from '../utils/sessionStorage'

export function useChatStream() {
  const [currentSession, setCurrentSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const isStreamingRef = useRef(false)
  const abortRef = useRef(null)
  const idCounter = useRef(0)
  const tokenBufferRef = useRef('')
  const activeAssistantIdRef = useRef(null)

  // Initialize session on mount
  useEffect(() => {
    const activeId = getActiveSessionId()
    if (activeId) {
      const session = getSession(activeId)
      if (session) {
        setCurrentSession(session)
        setMessages(session.messages || [])
        return
      }
    }
    // If no active session, start empty
    setMessages([])
  }, [])

  // Persist messages to the current session whenever they change
  useEffect(() => {
    if (currentSession && messages.length > 0) {
      // Don't save if it's currently streaming to avoid spamming localStorage?
      // Actually, saving on stream end is better, but doing it on every update is fine for local.
      // We will only persist when NOT loading.
      if (!isLoading) {
        const updated = {
          ...currentSession,
          messages: messages.map(m => ({ ...m, isStreaming: false }))
        }
        saveSession(updated)
        setCurrentSession(updated)
      }
    }
  }, [messages, isLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  const nextId = () => {
    idCounter.current += 1
    return `msg-${idCounter.current}-${Date.now()}`
  }

  const clearChat = useCallback(() => {
    const session = createNewSession()
    saveSession(session)
    setActiveSession(session.id)
    setCurrentSession(session)
    setMessages([])
    setError(null)
    if (abortRef.current) abortRef.current()
  }, [])

  const loadSession = useCallback((sessionId) => {
    const session = getSession(sessionId)
    if (session) {
      setActiveSession(session.id)
      setCurrentSession(session)
      setMessages(session.messages || [])
      setError(null)
      if (abortRef.current) abortRef.current()
    }
  }, [])

  const send = useCallback((query) => {
    if (!query.trim() || isLoading) return
    if (isStreamingRef.current) return

    isStreamingRef.current = true
    tokenBufferRef.current = ''
    setError(null)

    let sessionToUse = currentSession
    if (!sessionToUse) {
      sessionToUse = createNewSession()
      setActiveSession(sessionToUse.id)
      setCurrentSession(sessionToUse)
    }

    // Set title on first message
    if (!sessionToUse.title || sessionToUse.title === "New chat" || sessionToUse.messages.length === 0) {
      sessionToUse.title = query.trim().slice(0, 40) + "..."
      saveSession(sessionToUse)
      setCurrentSession({ ...sessionToUse })
    }

    const userMsg = {
      id: nextId(),
      role: 'user',
      content: query.trim(),
      timestamp: new Date().toISOString(),
      citations: [],
      isStreaming: false,
      isError: false,
    }

    const assistantId = nextId()
    activeAssistantIdRef.current = assistantId
    const assistantMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      citations: [],
      isStreaming: true,
      isError: false,
    }

    const currentMessages = [...messages]
    const chatHistory = currentMessages
      .filter(m => m.content && !m.isError)
      .map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setIsLoading(true)

    const abort = sendChatMessage(query.trim(), chatHistory, {
      onChunk(text) {
        tokenBufferRef.current += text
        const snapshot = tokenBufferRef.current
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: snapshot }
              : m
          )
        )
      },

      onCitations(citations) {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, citations }
              : m
          )
        )
      },

      onDone() {
        isStreamingRef.current = false
        const finalContent = tokenBufferRef.current
        setMessages(prev =>
          prev.map(m => {
            if (m.id !== assistantId) return m
            if (!finalContent && !m.isError) {
              return {
                ...m,
                content: 'No response received. Please try again.',
                isStreaming: false,
                isError: true,
              }
            }
            return { ...m, content: finalContent, isStreaming: false }
          })
        )
        setIsLoading(false)
      },

      onError(errMsg) {
        isStreamingRef.current = false
        setError(errMsg)
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? {
                  ...m,
                  content: errMsg || 'Something went wrong. Please try again.',
                  isStreaming: false,
                  isError: true,
                }
              : m
          )
        )
        setIsLoading(false)
      },
    })

    abortRef.current = abort
  }, [isLoading, messages, currentSession])

  return { messages, send, isLoading, error, clearChat, loadSession, currentSession }
}
