/**
 * Converts an ISO timestamp to a relative label ("2h ago", "3d ago", etc.)
 */
export function relativeTime(isoString) {
  if (!isoString) return ''
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diff = Math.max(0, now - then)

  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}d ago`
  const w = Math.floor(d / 7)
  return `${w}w ago`
}

/**
 * Category → placeholder gradient colors for thumbnail fallback
 */
const CATEGORY_GRADIENTS = {
  LLMs: ['#7F77DD', '#5F58B8'],
  'Hardware/Chips': ['#3ECFB4', '#2BA898'],
  Hardware: ['#3ECFB4', '#2BA898'],
  'Startups/Funding': ['#F0A96D', '#D8854A'],
  Startups: ['#F0A96D', '#D8854A'],
  'Policy/Regulation': ['#F06D6D', '#D84A4A'],
  Policy: ['#F06D6D', '#D84A4A'],
  Robotics: ['#71717A', '#52525B'],
  Research: ['#6366F1', '#4F46E5'],
  'Industry News': ['#0EA5E9', '#0284C7'],
  Other: ['#A1A1AA', '#71717A'],
}

export function categoryGradient(category) {
  return CATEGORY_GRADIENTS[category] ?? CATEGORY_GRADIENTS.Other
}

/**
 * Filter chips — matches the backend classifier categories
 */
export const FILTER_CHIPS = [
  'All',
  'LLMs',
  'Hardware/Chips',
  'Robotics',
  'Startups/Funding',
  'Policy/Regulation',
  'Research',
  'Industry News',
  'Other',
]
