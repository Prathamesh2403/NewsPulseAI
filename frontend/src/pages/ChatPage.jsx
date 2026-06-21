import { useRef, useEffect } from 'react'
import { useChatStream } from '../hooks/useChatStream'
import ChatLayout from '../components/layout/ChatLayout'
import ChatBubble from '../components/chat/ChatBubble'
import ChatInput from '../components/chat/ChatInput'
import EmptyState from '../components/chat/EmptyState'

export default function ChatPage() {
  const { messages, send, isLoading, clearChat, loadSession, currentSession } = useChatStream()
  const messagesEndRef = useRef(null)
  const scrollContainerRef = useRef(null)

  // Auto-scroll to bottom on new messages or streaming content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const hasMessages = messages.length > 0

  return (
    <ChatLayout onNewChat={clearChat} loadSession={loadSession} currentSession={currentSession}>
      <div className="chat-page">
        {/* Message area */}
        <div ref={scrollContainerRef} className="chat-messages-area">
          {!hasMessages ? (
            <EmptyState onSend={send} />
          ) : (
            <div className="chat-messages-container">
              {messages.map(msg => (
                <ChatBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input bar */}
        <ChatInput onSend={send} disabled={isLoading} />
      </div>
    </ChatLayout>
  )
}
