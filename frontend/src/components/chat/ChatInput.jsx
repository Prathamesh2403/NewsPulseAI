import { useState, useRef, useEffect } from 'react'

/* ── Icons ─────────────────────────────────────────────────────────── */
function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22 11 13 2 9z" />
    </svg>
  )
}

function MicIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  )
}

function PaperclipIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  )
}

/**
 * ChatInput — fixed-bottom input bar with send, mic, and attachment buttons.
 *
 * - Enter sends (unless Shift+Enter for multiline)
 * - Disabled while waiting for assistant response
 */
export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [value])

  function handleSubmit() {
    if (!value.trim() || disabled) return
    onSend(value)
    setValue('')
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div
      className="shrink-0"
      style={{
        padding: '12px 24px 16px',
        borderTop: '1px solid var(--color-gray-200)',
        backgroundColor: 'var(--color-surface)',
      }}
    >
      <div
        className="flex items-end"
        style={{
          maxWidth: 820,
          margin: '0 auto',
          backgroundColor: 'var(--color-gray-50)',
          borderRadius: 24,
          border: '1px solid var(--color-gray-200)',
          padding: '6px 6px 6px 16px',
          transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
          boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
        }}
        onFocusCapture={e => {
          e.currentTarget.style.borderColor = 'var(--color-primary-light)'
          e.currentTarget.style.boxShadow = '0 0 0 3px rgba(127,119,221,0.10)'
        }}
        onBlurCapture={e => {
          if (!e.currentTarget.contains(e.relatedTarget)) {
            e.currentTarget.style.borderColor = 'var(--color-gray-200)'
            e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.03)'
          }
        }}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask about AI and tech news..."
          rows={1}
          className="flex-1 resize-none outline-none bg-transparent"
          style={{
            fontSize: 14,
            lineHeight: 1.5,
            color: 'var(--color-gray-800)',
            padding: '6px 0',
            maxHeight: 120,
            fontFamily: 'var(--font-sans)',
          }}
        />

        {/* Action buttons */}
        <div className="flex items-center gap-1 shrink-0" style={{ marginBottom: 2 }}>
          {/* Mic */}
          <button
            type="button"
            className="p-2 rounded-full transition-colors"
            style={{ color: 'var(--color-gray-400)', background: 'transparent' }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--color-gray-200)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            aria-label="Voice input"
            tabIndex={-1}
          >
            <MicIcon />
          </button>

          {/* Attachment */}
          <button
            type="button"
            className="p-2 rounded-full transition-colors"
            style={{ color: 'var(--color-gray-400)', background: 'transparent' }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--color-gray-200)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            aria-label="Attach file"
            tabIndex={-1}
          >
            <PaperclipIcon />
          </button>

          {/* Send */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            className="flex items-center justify-center rounded-full transition-all duration-150"
            style={{
              width: 36,
              height: 36,
              background: value.trim() && !disabled
                ? 'var(--color-primary)'
                : 'var(--color-gray-300)',
              cursor: value.trim() && !disabled ? 'pointer' : 'not-allowed',
              border: 'none',
              opacity: value.trim() && !disabled ? 1 : 0.7,
            }}
            onMouseEnter={e => {
              if (value.trim() && !disabled) {
                e.currentTarget.style.background = 'var(--color-primary-dark)'
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={e => {
              if (value.trim() && !disabled) {
                e.currentTarget.style.background = 'var(--color-primary)'
                e.currentTarget.style.transform = 'scale(1)'
              }
            }}
            aria-label="Send message"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  )
}
