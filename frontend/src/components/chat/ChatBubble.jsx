import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import CitationCard from './CitationCard'
import TypingIndicator from './TypingIndicator'

function formatTime(date) {
  if (!date) return ''
  const d = date instanceof Date ? date : new Date(date)
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function BotAvatar() {
  return (
    <div className="bot-avatar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7F77DD" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    </div>
  )
}

export default function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  const isStreaming = message.isStreaming
  const hasContent = !!message.content
  const hasCitations = !isUser && message.citations?.length > 0 && !isStreaming

  // Show typing indicator if it's the assistant, it's streaming, and we haven't received content yet
  const showTyping = !isUser && isStreaming && !hasContent

  return (
    <div className={`chat-message ${isUser ? 'chat-message--user' : 'chat-message--assistant'}`}>
      {/* Assistant avatar */}
      {!isUser && (
        <div className="chat-message-avatar">
          <BotAvatar />
        </div>
      )}

      <div className="chat-message-body">
        {/* Message content */}
        <div className={`chat-message-content ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'} ${message.isError ? 'chat-bubble-error' : ''} ${isStreaming && hasContent ? 'streaming-cursor' : ''}`}>
          {showTyping ? (
            <TypingIndicator />
          ) : isUser ? (
            message.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Timestamp */}
        <span className="chat-message-time">
          {formatTime(message.timestamp)}
        </span>

        {/* Citations — max 3, hidden while streaming */}
        {hasCitations && (
          <div className="chat-citations">
            <p className="chat-citations-label">Sources</p>
            <div className="chat-citations-row">
              {message.citations.slice(0, 3).map((c, i) => (
                <CitationCard key={c.id || c.url || i} citation={c} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
