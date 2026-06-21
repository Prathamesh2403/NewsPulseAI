import { useState, useEffect } from 'react'
import { getAuthHeaders, removeToken } from '../utils/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

/**
 * useArticles — fetches paginated articles from the real API.
 * Supports category filtering.
 */
export function useArticles(category = null, page = 1) {
  const [articles, setArticles] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)

    const params = new URLSearchParams({ page: String(page), limit: '20' })
    if (category && category !== 'All') {
      params.append('category', category)
    }

    fetch(`${API_BASE}/api/v1/articles?${params}`, {
      headers: { ...getAuthHeaders() }
    })
      .then(r => {
        if (!r.ok) {
          if (r.status === 401) {
            removeToken();
            window.location.href = '/login';
          }
          throw new Error(`HTTP ${r.status}`)
        }
        return r.json()
      })
      .then(data => {
        setArticles(data.articles || [])
        setTotal(data.total || 0)
        setTotalPages(data.total_pages || 1)
        setLoading(false)
      })
      .catch(e => {
        console.error('useArticles error:', e)
        setError(e.message)
        setLoading(false)
      })
  }, [category, page])

  return { articles, total, totalPages, loading, error }
}

/**
 * useFeaturedArticles — fetches top 5 articles for "Today's Pick" sidebar.
 */
export function useFeaturedArticles() {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/articles/featured`, {
      headers: { ...getAuthHeaders() }
    })
      .then(r => {
        if (!r.ok) {
          if (r.status === 401) {
            removeToken();
            window.location.href = '/login';
          }
          throw new Error(`HTTP ${r.status}`)
        }
        return r.json()
      })
      .then(data => {
        setArticles(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(e => {
        console.error('useFeaturedArticles error:', e)
        setError(e.message)
        setLoading(false)
      })
  }, [])

  return { articles, loading, error }
}
