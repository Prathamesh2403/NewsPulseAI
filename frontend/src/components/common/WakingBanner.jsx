/**
 * WakingBanner — shown while Render Free Tier is spinning up.
 *
 * Renders a fixed top banner with a spinner and a friendly message.
 * Automatically disappears once the backend responds (isWaking becomes false).
 * Requires @keyframes spin to be defined in index.css.
 */
export function WakingBanner({ isWaking }) {
  if (!isWaking) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: '#1e40af',
        color: 'white',
        textAlign: 'center',
        padding: '10px 16px',
        fontSize: '14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '10px',
      }}
    >
      <span
        style={{
          display: 'inline-block',
          width: 14,
          height: 14,
          border: '2px solid rgba(255,255,255,0.3)',
          borderTopColor: 'white',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          flexShrink: 0,
        }}
      />
      Server is starting up — this takes about 30 seconds on first visit. Thank you for your patience.
    </div>
  )
}
