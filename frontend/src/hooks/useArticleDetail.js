import { useState, useEffect } from 'react'
import { getAuthHeaders, removeToken } from '../utils/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

/**
 * useArticleDetail — fetches a single article with Reddit comments from real API.
 */
export function useArticleDetail(id) {
  const [article, setArticle] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!id) return

    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/v1/articles/${id}`, {
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
        setArticle(data)
        setLoading(false)
      })
      .catch(e => {
        console.error('useArticleDetail error:', e)
        setError(e.message)
        setLoading(false)
      })
  }, [id])

  return { article, loading, error }
}
