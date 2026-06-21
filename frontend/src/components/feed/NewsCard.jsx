import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { categoryGradient } from '../../utils/feedUtils'
import { relativeTime } from '../../utils/feedUtils'

/**
 * NewsCard — grid card with top image, category badge, headline, source, sentiment.
 * Uses real API field names: image_url, source_name, published_at, sentiment_label, summary.
 */
export default function NewsCard({ article }) {
  const navigate = useNavigate()
  const [imgError, setImgError] = useState(false)

  const gradient = categoryGradient(article.category)
  const hasImage = article.image_url && !imgError

  function handleClick() {
    navigate(`/article/${article.id}`)
  }

  return (
    <article className="news-card" onClick={handleClick} role="button" tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') handleClick() }}
    >
      {/* Image area */}
      <div className="news-card__image-wrap">
        {article.image_url && !imgError ? (
          <img
            src={article.image_url}
            alt={article.title}
            className="news-card__image"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        ) : null}
        <div
          className="news-card__image-fallback"
          style={{
            display: hasImage ? 'none' : 'flex',
            background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
          }}
        >
          <span>{article.category || 'News'}</span>
        </div>
      </div>

      {/* Content */}
      <div className="news-card__body">
        {/* Category badge */}
        <span className="news-card__category" style={{ color: gradient[0] }}>
          {article.category || 'General'}
        </span>

        {/* Headline */}
        <h3 className="news-card__title">{article.title}</h3>

        {/* Source + timestamp */}
        <p className="news-card__meta">
          <span className="news-card__source">{article.source_name || article.source}</span>
          {' \u00B7 '}
          {relativeTime(article.published_at)}
        </p>

        {/* Snippet */}
        {article.summary && (
          <p className="news-card__snippet">{article.summary}</p>
        )}
      </div>
    </article>
  )
}
