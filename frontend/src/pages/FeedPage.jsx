import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useArticles, useFeaturedArticles } from '../hooks/useArticles'
import FilterChips from '../components/feed/FilterChips'
import NewsCard from '../components/feed/NewsCard'
import SentimentBadge from '../components/feed/SentimentBadge'
import { relativeTime, categoryGradient } from '../utils/feedUtils'

/* ── Hero skeleton ──────────────────────────────────────────────────── */
function HeroSkeleton() {
  return (
    <div className="hero-section animate-pulse" style={{ background: 'var(--color-gray-200)' }}>
      <div className="hero-overlay" />
      <div className="hero-content">
        <div style={{ width: 80, height: 24, borderRadius: 20, background: 'rgba(255,255,255,0.15)' }} />
        <div style={{ width: '70%', height: 32, borderRadius: 8, background: 'rgba(255,255,255,0.12)', marginTop: 16 }} />
        <div style={{ width: '50%', height: 20, borderRadius: 6, background: 'rgba(255,255,255,0.08)', marginTop: 12 }} />
      </div>
    </div>
  )
}

/* ── Card skeleton ──────────────────────────────────────────────────── */
function CardSkeleton() {
  return (
    <div className="news-card animate-pulse" style={{ cursor: 'default' }}>
      <div className="news-card__image-wrap" style={{ background: 'var(--color-gray-100)' }} />
      <div className="news-card__body">
        <div style={{ width: 60, height: 10, borderRadius: 6, background: 'var(--color-gray-100)' }} />
        <div style={{ width: '90%', height: 14, borderRadius: 6, background: 'var(--color-gray-100)', marginTop: 8 }} />
        <div style={{ width: '70%', height: 14, borderRadius: 6, background: 'var(--color-gray-100)', marginTop: 6 }} />
        <div style={{ width: '40%', height: 10, borderRadius: 6, background: 'var(--color-gray-100)', marginTop: 10 }} />
      </div>
    </div>
  )
}

/* ── Sidebar skeleton ───────────────────────────────────────────────── */
function SidebarSkeleton() {
  return (
    <div className="todays-pick">
      <h2 className="todays-pick__heading">Today's Pick</h2>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="todays-pick__item animate-pulse" style={{ cursor: 'default' }}>
          <div className="todays-pick__thumb" style={{ background: 'var(--color-gray-100)' }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ width: 40, height: 8, borderRadius: 4, background: 'var(--color-gray-100)' }} />
            <div style={{ width: '90%', height: 12, borderRadius: 4, background: 'var(--color-gray-100)' }} />
            <div style={{ width: '50%', height: 8, borderRadius: 4, background: 'var(--color-gray-100)' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

/* ── Hero Section ───────────────────────────────────────────────────── */
function HeroSection({ article }) {
  const navigate = useNavigate()

  if (!article) return <HeroSkeleton />

  const gradient = categoryGradient(article.category)
  const hasImage = !!article.image_url

  return (
    <div
      className="hero-section"
      onClick={() => navigate(`/article/${article.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter') navigate(`/article/${article.id}`) }}
      style={{
        backgroundImage: hasImage ? `url(${article.image_url})` : `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      <div className="hero-overlay" />
      <div className="hero-content">
        <span className="hero-category" style={{ background: gradient[0] }}>
          {article.category || 'News'}
        </span>
        <h1 className="hero-title">{article.title}</h1>
        <div className="hero-meta">
          <span className="hero-source">{article.source_name || article.source}</span>
          <span className="hero-dot">&middot;</span>
          <span>{relativeTime(article.published_at)}</span>
          <SentimentBadge sentiment={article.sentiment_label || 'neutral'} />
        </div>
      </div>
    </div>
  )
}

/* ── Today's Pick Sidebar ───────────────────────────────────────────── */
function TodaysPickSidebar() {
  const { articles, loading } = useFeaturedArticles()
  const navigate = useNavigate()

  if (loading) return <SidebarSkeleton />

  if (!articles.length) {
    return (
      <div className="todays-pick">
        <h2 className="todays-pick__heading">Today's Pick</h2>
        <p style={{ fontSize: 13, color: 'var(--color-gray-400)', padding: '16px 0' }}>
          No featured articles yet.
        </p>
      </div>
    )
  }

  return (
    <div className="todays-pick">
      <h2 className="todays-pick__heading">Today's Pick</h2>
      {articles.map((article, i) => {
        const gradient = categoryGradient(article.category)
        return (
          <div
            key={article.id}
            className="todays-pick__item"
            onClick={() => navigate(`/article/${article.id}`)}
            role="button"
            tabIndex={0}
            onKeyDown={e => { if (e.key === 'Enter') navigate(`/article/${article.id}`) }}
          >
            {/* Thumbnail */}
            {article.image_url ? (
              <img
                src={article.image_url}
                alt={article.title}
                className="todays-pick__thumb"
                onError={e => {
                  e.target.style.display = 'none'
                  e.target.nextSibling.style.display = 'flex'
                }}
                loading="lazy"
              />
            ) : null}
            <div
              className="todays-pick__thumb-fallback"
              style={{
                display: article.image_url ? 'none' : 'flex',
                background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
              }}
            >
              <span>{(article.category || 'N')[0]}</span>
            </div>

            {/* Text */}
            <div className="todays-pick__text">
              <span className="todays-pick__category" style={{ color: gradient[0] }}>
                {(article.category || 'General').toUpperCase()}
              </span>
              <p className="todays-pick__title">{article.title}</p>
              <span className="todays-pick__meta">
                {article.source_name || article.source}
                {' \u00B7 '}
                {relativeTime(article.published_at)}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── FeedPage ────────────────────────────────────────────────────────── */
export default function FeedPage() {
  const [activeFilter, setActiveFilter] = useState('All')
  const { articles, loading, error } = useArticles(
    activeFilter === 'All' ? null : activeFilter
  )

  // Use first article with an image as the hero
  const heroArticle = useMemo(() => {
    if (!articles.length) return null
    return articles.find(a => a.image_url) || articles[0]
  }, [articles])

  // Grid articles = all except hero
  const gridArticles = useMemo(() => {
    if (!heroArticle) return articles
    return articles.filter(a => a.id !== heroArticle.id)
  }, [articles, heroArticle])

  return (
    <div className="feed-page animate-fade-in">

      {/* ── Hero ─────────────────────────────────────────────────── */}
      {loading ? <HeroSkeleton /> : <HeroSection article={heroArticle} />}

      {/* ── Main content area ────────────────────────────────────── */}
      <div className="feed-layout">

        {/* LEFT — Articles */}
        <section className="feed-main">
          {/* Filter chips */}
          <div style={{ marginBottom: 24 }}>
            <FilterChips active={activeFilter} onChange={setActiveFilter} />
          </div>

          {/* Loading skeletons */}
          {loading && (
            <div className="feed-grid">
              {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="feed-empty">
              <p style={{ color: 'var(--color-coral)' }}>Failed to load articles. Please try again later.</p>
            </div>
          )}

          {/* Empty */}
          {!loading && !error && gridArticles.length === 0 && (
            <div className="feed-empty">
              <span style={{ fontSize: 36 }}>&#128269;</span>
              <p style={{ fontWeight: 600, color: 'var(--color-gray-700)', fontSize: 15 }}>
                No articles in this category yet
              </p>
              <p style={{ color: 'var(--color-gray-400)', fontSize: 13 }}>
                Try a different filter or check back later.
              </p>
            </div>
          )}

          {/* Article grid */}
          {!loading && !error && gridArticles.length > 0 && (
            <div className="feed-grid">
              {gridArticles.map(article => (
                <NewsCard key={article.id} article={article} />
              ))}
            </div>
          )}
        </section>

        {/* RIGHT — Today's Pick */}
        <aside className="feed-sidebar">
          <TodaysPickSidebar />
        </aside>

      </div>
    </div>
  )
}
