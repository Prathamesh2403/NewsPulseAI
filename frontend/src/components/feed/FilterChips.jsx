import { FILTER_CHIPS } from '../../utils/feedUtils'

export default function FilterChips({ active, onChange }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {FILTER_CHIPS.map(chip => {
        const isActive = chip === active
        return (
          <button
            key={chip}
            onClick={() => onChange(chip)}
            className="cursor-pointer"
            style={{
              padding: '6px 16px',
              fontSize: 13,
              fontWeight: isActive ? 600 : 500,
              borderRadius: 20,
              border: 'none',
              transition: 'all 0.15s ease',
              background: isActive ? 'var(--color-primary)' : 'rgba(0,0,0,0.05)',
              color: isActive ? '#fff' : 'var(--color-gray-600)',
              boxShadow: isActive ? '0 2px 8px rgba(127,119,221,0.30)' : 'none',
            }}
            onMouseEnter={e => {
              if (!isActive) {
                e.currentTarget.style.background = 'var(--color-primary-subtle)'
                e.currentTarget.style.color = 'var(--color-primary)'
              }
            }}
            onMouseLeave={e => {
              if (!isActive) {
                e.currentTarget.style.background = 'rgba(0,0,0,0.05)'
                e.currentTarget.style.color = 'var(--color-gray-600)'
              }
            }}
          >
            {chip}
          </button>
        )
      })}
    </div>
  )
}
