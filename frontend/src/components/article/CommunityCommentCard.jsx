/**
 * CommunityCommentCard — displays a single community comment (HN, Reddit, DEV.to).
 * Works with real API fields: { username, body, upvotes, permalink, source }
 */

function UpArrowIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 10V2" />
      <path d="M2.5 5.5L6 2l3.5 3.5" />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="5.5" r="3" />
      <path d="M2.5 14c0-3 2.5-4.5 5.5-4.5s5.5 1.5 5.5 4.5" />
    </svg>
  )
}

export default function CommunityCommentCard({ comment }) {
  // Support both API shape (body) and legacy (text)
  const body = comment.body || comment.text || ''
  const username = comment.username || 'anonymous'
  const upvotes = comment.upvotes ?? 0
  const source = comment.source || 'reddit'

  const sourceLabels = {
    reddit: 'Reddit',
    hackernews: 'Hacker News',
    devto: 'DEV.to',
  }

  const sourceColors = {
    reddit: '#ff4500',
    hackernews: '#ff6600',
    devto: '#0a0a0a',
  }

  return (
    <div className="reddit-comment">
      {/* Header: avatar + username + upvotes */}
      <div className="reddit-comment__header">
        <div className="reddit-comment__user">
          <div className="reddit-comment__avatar" style={{ color: sourceColors[source] }}>
            <UserIcon />
          </div>
          <span className="reddit-comment__username">{username}</span>
          <span style={{ fontSize: '11px', color: 'var(--color-gray-400)', marginLeft: 8 }}>
            via {sourceLabels[source] || source}
          </span>
        </div>
        <div className="reddit-comment__votes">
          <UpArrowIcon />
          <span>{upvotes}</span>
        </div>
      </div>

      {/* Body */}
      <p className="reddit-comment__body">{body}</p>

      {/* Upvote badge */}
      <div className="reddit-comment__footer">
        <span className="reddit-comment__badge" style={{ color: sourceColors[source] }}>
          <UpArrowIcon />
          {upvotes}
        </span>
      </div>
    </div>
  )
}
