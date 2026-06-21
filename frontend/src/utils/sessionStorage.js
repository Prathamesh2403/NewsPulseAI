import { nanoid } from 'nanoid'

const SESSIONS_KEY = "newspulse_sessions"
const ACTIVE_KEY = "newspulse_active_session"

export function getAllSessions() {
    try {
        return JSON.parse(localStorage.getItem(SESSIONS_KEY)) || []
    } catch { return [] }
}

export function getActiveSessionId() {
    return localStorage.getItem(ACTIVE_KEY)
}

export function getSession(sessionId) {
    return getAllSessions().find(s => s.id === sessionId) || null
}

export function saveSession(session) {
    const sessions = getAllSessions()
    const index = sessions.findIndex(s => s.id === session.id)
    if (index >= 0) {
        sessions[index] = session   // update existing
    } else {
        sessions.unshift(session)   // add new at top
    }
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

export function setActiveSession(sessionId) {
    localStorage.setItem(ACTIVE_KEY, sessionId)
}

export function deleteSession(sessionId) {
    const sessions = getAllSessions().filter(s => s.id !== sessionId)
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
    
    // if deleted session was active, clear active session
    if (getActiveSessionId() === sessionId) {
        localStorage.removeItem(ACTIVE_KEY)
    }
}

export function createNewSession() {
    return {
        id: `sess_${nanoid(8)}`,
        title: "New chat",
        createdAt: new Date().toISOString(),
        messages: []
    }
}
