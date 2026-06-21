/**
 * SentimentBadge — color-coded filled pill.
 */
const CONFIG = {
  positive: {
    label: 'Positive',
    bg: 'rgba(62, 207, 180, 0.14)',
    color: '#0F8A6F',
  },
  neutral: {
    label: 'Neutral',
    bg: 'rgba(113, 113, 122, 0.10)',
    color: '#52525B',
  },
  negative: {
    label: 'Negative',
    bg: 'rgba(240, 109, 109, 0.14)',
    color: '#B83D3D',
  },
}

export default function SentimentBadge({ sentiment }) {
  const cfg = CONFIG[sentiment] ?? CONFIG.neutral

  return (
    <span
      className="inline-flex items-center justify-center px-3 py-1 text-[11px] font-semibold whitespace-nowrap shrink-0"
      style={{
        background: cfg.bg,
        color: cfg.color,
        borderRadius: 20,
        letterSpacing: '0.01em',
      }}
    >
      {cfg.label}
    </span>
  )
}
