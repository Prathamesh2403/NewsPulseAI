export default function EmptyState({ onSend }) {
  const suggestions = [
    { icon: '🔥', text: "What's trending in AI today?" },
    { icon: '📰', text: 'Summarize today\'s top tech stories' },
    { icon: '🤖', text: 'Latest news on LLMs' },
    { icon: '💡', text: 'How is the AI chip market doing?' },
  ]

  return (
    <div className="chat-empty-state">
      {/* Logo */}
      <div className="chat-empty-logo">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#7F77DD" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      </div>

      <h1 className="chat-empty-heading">What's on your mind today?</h1>
      <p className="chat-empty-subtitle">
        Ask about the latest AI and tech news, trends, or stories
      </p>

      {/* 2x2 Suggestion Grid */}
      <div className="chat-suggestions-grid">
        {suggestions.map(s => (
          <button
            key={s.text}
            className="chat-suggestion-card"
            onClick={() => onSend?.(s.text)}
          >
            <span className="chat-suggestion-icon">{s.icon}</span>
            <span className="chat-suggestion-text">{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
