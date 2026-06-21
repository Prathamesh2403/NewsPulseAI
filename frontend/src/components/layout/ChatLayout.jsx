import { useState } from 'react'
import Sidebar from './Sidebar'

export default function ChatLayout({ children, onNewChat, loadSession, currentSession }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="chat-layout">
      <Sidebar
        onNewChat={onNewChat}
        loadSession={loadSession}
        currentSession={currentSession}
        isCollapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(prev => !prev)}
      />
      <div className="chat-main">
        {children}
      </div>
    </div>
  )
}
