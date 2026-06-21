import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useArticleDetail } from '../hooks/useArticleDetail'
import { categoryGradient } from '../utils/feedUtils'
import { ArticleChatSidebar } from '../components/article/ArticleChatSidebar'

/* ── Icons ────────────────────────────────────────────────────────── */
function ArrowLeftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 12L6 8l4-4" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4.5 3L7.5 6l-3 3" />
    </svg>
  )
}

function ExternalLinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.5 7.5v3.5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1h3.5" />
      <path d="M8 2h4v4" />
      <path d="M5.5 8.5L12 2" />
    </svg>
  )
}

/* ── Date formatter ───────────────────────────────────────────────── */
function formatFullDate(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

/* ── Skeleton loader ──────────────────────────────────────────────── */
function DetailSkeleton() {
  return (
    <div className="article-detail animate-fade-in">
      <div className="animate-pulse" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ height: 14, width: 80, borderRadius: 6, background: 'var(--color-gray-100)' }} />
        <div style={{ height: 10, width: 260, borderRadius: 6, background: 'var(--color-gray-100)' }} />
        <div style={{ display: 'flex', gap: 28, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ height: 28, width: '90%', borderRadius: 8, background: 'var(--color-gray-100)' }} />
            <div style={{ height: 12, width: '40%', borderRadius: 6, background: 'var(--color-gray-100)' }} />
            <div style={{ height: 360, borderRadius: 'var(--radius)', background: 'var(--color-gray-100)' }} />
            <div style={{ height: 12, width: '100%', borderRadius: 6, background: 'var(--color-gray-100)' }} />
            <div style={{ height: 12, width: '95%', borderRadius: 6, background: 'var(--color-gray-100)' }} />
          </div>
          <div style={{ width: 340, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ height: 600, borderRadius: 'var(--radius-lg)', background: 'var(--color-gray-100)' }} />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── ArticleDetailPage ────────────────────────────────────────────── */
export default function ArticleDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { article, loading, error } = useArticleDetail(id)
  const [imgError, setImgError] = useState(false)

  if (loading) return <DetailSkeleton />

  if (error || !article) {
    return (
      <div className="article-detail animate-fade-in">
        <div
          className="bg-white"
          style={{
            borderRadius: 'var(--radius)',
            boxShadow: 'var(--shadow-card)',
            padding: '48px 24px',
            textAlign: 'center',
            color: 'var(--color-coral)',
            fontSize: 15,
          }}
        >
          Article not found or failed to load.
        </div>
      </div>
    )
  }

  const gradient = categoryGradient(article.category)
  const hasImage = article.image_url && !imgError

  // Split content into paragraphs
  const contentParagraphs = (article.content || '').split('\n').filter(p => p.trim())

  return (
    <div className="article-detail animate-fade-in">

      {/* ── Back button ──────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/')}
        className="article-detail__back"
      >
        <ArrowLeftIcon />
        Back to Feed
      </button>

      {/* ── Breadcrumb ───────────────────────────────────────────── */}
      <nav className="article-detail__breadcrumb" aria-label="Breadcrumb">
        <span className="article-detail__breadcrumb-link" onClick={() => navigate('/')}>Home</span>
        <ChevronRightIcon />
        <span>{article.category || 'General'}</span>
        <ChevronRightIcon />
        <span className="article-detail__breadcrumb-current">{article.title}</span>
      </nav>

      {/* ── Main layout ──────────────────────────────────────────── */}
      <div className="article-detail__layout">

        {/* LEFT — Article content */}
        <article className="article-detail__content">

          {/* Headline */}
          <h1 className="article-detail__title">{article.title}</h1>

          {/* Source + date + category */}
          <div className="article-detail__meta-row">
            <span className="article-detail__source-badge">
              {article.source_name || article.source}
            </span>
            <span className="article-detail__date">
              {formatFullDate(article.published_at)}
            </span>
            <span className="article-detail__category-pill" style={{ color: gradient[0] }}>
              {article.category || 'General'}
            </span>

            {/* Read original link */}
            {article.url && (
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="article-detail__original-link"
                onClick={e => e.stopPropagation()}
              >
                <ExternalLinkIcon />
                Read original
              </a>
            )}
          </div>

          {/* Hero image */}
          <div className="article-detail__hero-image">
            {hasImage ? (
              <img
                src={article.image_url}
                alt={article.title}
                onError={() => setImgError(true)}
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              />
            ) : (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
                  color: 'rgba(255,255,255,0.6)',
                  fontSize: 48,
                }}
              >
                &#128240;
              </div>
            )}
          </div>

          {/* Summary callout */}
          {article.summary && (
            <div className="article-detail__summary">
              <strong>Summary:</strong> {article.summary}
            </div>
          )}

          {/* Article body */}
          <div className="article-detail__body">
            {contentParagraphs.map((paragraph, i) => (
              <p key={i} className="article-detail__paragraph">
                {i === 0 && paragraph.includes('.') ? (
                  <>
                    <strong style={{ color: 'var(--color-gray-900)' }}>
                      {paragraph.split('.')[0]}.
                    </strong>
                    {paragraph.slice(paragraph.indexOf('.') + 1)}
                  </>
                ) : paragraph}
              </p>
            ))}
          </div>
        </article>

        {/* RIGHT — Chat Sidebar */}
        <aside className="article-detail__sidebar">
          <ArticleChatSidebar articleId={id} articleTitle={article.title} />
        </aside>

      </div>
    </div>
  )
}
