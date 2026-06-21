import { useState } from 'react'

/**
 * ArticleThumbnail
 * Renders a real <img> with rounded corners. Falls back to a category gradient
 * if the image fails to load or no src is provided.
 */
const CATEGORY_ICONS = {
  LLMs: '\u{1F916}',
  Hardware: '\u26A1',
  Startups: '\u{1F680}',
  Policy: '\u2696\uFE0F',
  Robotics: '\u{1F9BE}',
  Other: '\u{1F4F0}',
}

const CATEGORY_GRADIENTS = {
  LLMs: ['#7F77DD', '#5F58B8'],
  Hardware: ['#3ECFB4', '#2BA898'],
  Startups: ['#F0A96D', '#D8854A'],
  Policy: ['#F06D6D', '#D84A4A'],
  Robotics: ['#71717A', '#52525B'],
  Other: ['#A1A1AA', '#71717A'],
}

export default function ArticleThumbnail({ src, category, alt, size = 80 }) {
  const [imgError, setImgError] = useState(false)
  const showPlaceholder = !src || imgError

  const gradient = CATEGORY_GRADIENTS[category] ?? CATEGORY_GRADIENTS.Other
  const icon = CATEGORY_ICONS[category] ?? CATEGORY_ICONS.Other

  if (showPlaceholder) {
    return (
      <div
        className="shrink-0 flex items-center justify-center text-2xl select-none"
        style={{
          width: size,
          height: size,
          background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
          borderRadius: 'var(--radius-sm)',
        }}
        aria-hidden="true"
      >
        {icon}
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setImgError(true)}
      className="shrink-0 object-cover"
      style={{
        width: size,
        height: size,
        borderRadius: 'var(--radius-sm)',
      }}
    />
  )
}
