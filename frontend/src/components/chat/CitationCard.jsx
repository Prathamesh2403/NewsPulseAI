import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

/* ── Source color palette (deterministic by source name) ──────────── */
const SOURCE_COLORS = [
  { bg: '#EDE9FE', text: '#6D28D9', border: '#DDD6FE' },  // purple
  { bg: '#DBEAFE', text: '#1D4ED8', border: '#BFDBFE' },  // blue
  { bg: '#D1FAE5', text: '#047857', border: '#A7F3D0' },  // green
  { bg: '#FEF3C7', text: '#B45309', border: '#FDE68A' },  // amber
  { bg: '#FCE7F3', text: '#BE185D', border: '#FBCFE8' },  // pink
  { bg: '#E0E7FF', text: '#4338CA', border: '#C7D2FE' },  // indigo
  { bg: '#CCFBF1', text: '#0F766E', border: '#99F6E4' },  // teal
  { bg: '#FFE4E6', text: '#BE123C', border: '#FECDD3' },  // rose
]

function getSourceColor(sourceName) {
  let hash = 0
  for (let i = 0; i < sourceName.length; i++) {
    hash = sourceName.charCodeAt(i) + ((hash << 5) - hash)
  }
  return SOURCE_COLORS[Math.abs(hash) % SOURCE_COLORS.length]
}

/**
 * CitationCard — displays a single source citation below an assistant message.
 * Clicking navigates to the article detail page.
 */
export default function CitationCard({ citation }) {
  const navigate = useNavigate()
  const [citationError, setCitationError] = useState(null)
  const colors = getSourceColor(citation.source || citation.source_name || 'Source')
  const sourceName = citation.source_name || citation.source || 'Source'
  const title = citation.title || 'Untitled article'

  async function handleClick() {
    if (citation.id && !citation.id.toString().startsWith("tavily_")) {
      try {
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/articles/${citation.id}`
        )
        if (res.status === 404) {
          setCitationError(citation.id)
          return
        }
      } catch {
        setCitationError(citation.id)
        return
      }
    }
    
    if (citation.url) {
      window.open(citation.url, "_blank")
    } else {
      navigate(`/article/${citation.id}`)
    }
  }

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-2.5 text-left cursor-pointer outline-none group"
      style={{
        padding: '8px 14px',
        borderRadius: 'var(--radius-sm)',
        backgroundColor: 'var(--color-surface)',
        boxShadow: 'var(--shadow-card)',
        border: 'none',
        transition: 'box-shadow 0.2s ease, transform 0.15s ease',
        maxWidth: 320,
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)'
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-card)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      {/* Source badge circle */}
      <div
        className="shrink-0 flex items-center justify-center text-[10px] font-bold rounded-full"
        style={{
          width: 28,
          height: 28,
          backgroundColor: colors.bg,
          color: colors.text,
          border: `1.5px solid ${colors.border}`,
        }}
      >
        {sourceName.charAt(0).toUpperCase()}
      </div>

      {/* Source + title */}
      <div className="min-w-0">
        {citationError === citation.id ? (
          <span style={{ fontSize: 11, color: "var(--color-coral)" }}>
              Article no longer available
          </span>
        ) : (
          <p
            className="line-clamp-1"
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--color-gray-700)',
              lineHeight: 1.3,
            }}
          >
            <span style={{ color: colors.text }}>{sourceName}</span>
            <span style={{ color: 'var(--color-gray-300)', margin: '0 5px' }}>{'\u00B7'}</span>
            <span style={{ fontWeight: 400, color: 'var(--color-gray-600)' }}>{title}</span>
          </p>
        )}
      </div>
    </button>
  )
}
