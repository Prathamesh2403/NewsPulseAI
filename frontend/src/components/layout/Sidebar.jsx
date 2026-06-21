import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAllSessions, deleteSession } from '../../utils/sessionStorage'

/* Icons */
function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  )
}

export default function Sidebar({ onNewChat, loadSession, currentSession, isCollapsed, onToggle }) {
  const [sessions, setSessions] = useState(() => getAllSessions())
  const [searchQuery, setSearchQuery] = useState('')
  const [hoveredSession, setHoveredSession] = useState(null)
  const navigate = useNavigate()

  // Refresh sessions periodically
  useEffect(() => {
    const interval = setInterval(() => setSessions(getAllSessions()), 2000)
    return () => clearInterval(interval)
  }, [])

  const filteredSessions = searchQuery
    ? sessions.filter(s => s.title?.toLowerCase().includes(searchQuery.toLowerCase()))
    : sessions

  const handleSessionClick = (sessionId) => {
    loadSession(sessionId)
  }

  function handleDeleteSession(sessionId) {
    deleteSession(sessionId)
    setSessions(getAllSessions())
    
    // if we deleted the active session, show empty state
    if (sessionId === currentSession?.id) {
        onNewChat() // this clears chat and starts a new session
    }
  }

  if (isCollapsed) {
    return (
      <div className="chat-sidebar chat-sidebar--collapsed">
        <button className="sidebar-toggle-btn" onClick={onToggle} aria-label="Expand sidebar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
    )
  }

  return (
    <div className="chat-sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7F77DD" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
            </svg>
          </div>
          <span className="sidebar-logo-text">NewsPulse AI</span>
        </div>
        <button className="sidebar-toggle-btn" onClick={onToggle} aria-label="Collapse sidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
      </div>

      {/* New Chat Button */}
      <button className="new-chat-btn" onClick={onNewChat}>
        <PlusIcon />
        <span>New chat</span>
      </button>

      {/* Home Button */}
      <button className="sidebar-home-btn" onClick={() => navigate('/')}>
        <HomeIcon />
        <span>Home</span>
      </button>

      {/* Search */}
      <div className="sidebar-search">
        <SearchIcon />
        <input
          type="text"
          placeholder="Search chats..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="sidebar-search-input"
        />
      </div>

      {/* Sessions */}
      <div className="sidebar-sessions">
        {filteredSessions.length > 0 && (
          <p className="sidebar-section-label">Recents</p>
        )}
        {filteredSessions.slice(0, 10).map(session => (
          <div 
              key={session.id}
              className="sidebar-session-item"
              style={{ 
                  display: "flex", 
                  alignItems: "center", 
                  padding: "8px 12px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  position: "relative"
              }}
              onMouseEnter={() => setHoveredSession(session.id)}
              onMouseLeave={() => setHoveredSession(null)}
              onClick={() => handleSessionClick(session.id)}
          >
              <div style={{ display: 'flex', alignItems: 'center', marginRight: 8, opacity: 0.8 }}>
                <ChatIcon />
              </div>
              <span style={{ flex: 1, fontSize: 13, overflow: "hidden", 
                            textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {session.title}
              </span>
              
              {hoveredSession === session.id && (
                  <button
                      onClick={(e) => {
                          e.stopPropagation()   // prevent session from being opened
                          handleDeleteSession(session.id)
                      }}
                      style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          padding: "2px 4px",
                          borderRadius: "4px",
                          color: "var(--color-coral)",
                          flexShrink: 0
                      }}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                  </button>
              )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">JD</div>
          <span className="sidebar-username">John D.</span>
        </div>
      </div>
    </div>
  )
}
