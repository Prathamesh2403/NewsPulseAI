/**
 * TypingIndicator - animated three-dot indicator shown while the
 * assistant is generating a response.
 */
export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1" style={{ padding: '4px 0' }}>
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="inline-block rounded-full"
          style={{
            width: 7,
            height: 7,
            backgroundColor: 'var(--color-gray-400)',
            animation: `chatPulse 1.4s ease-in-out ${i * 0.16}s infinite`,
          }}
        />
      ))}
    </div>
  )
}
