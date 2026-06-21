"""
GNews.io ingester.

Fetches AI/tech news from the GNews API (https://gnews.io).
Free tier: 100 requests/day, 10 articles per request, 1 req/sec.

Docs: https://gnews.io/docs/v4
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import generate_article_id
from app.schemas.article import RawArticle

logger = get_logger(__name__)

_BASE_URL = "https://gnews.io/api/v4/search"

_QUERIES = [
    "artificial intelligence",
    "machine learning",
    "OpenAI OR Anthropic OR Gemini",
    "AI chips GPU",
    "AI regulation policy",
]

_MAX_RESULTS_PER_QUERY = 10  # Free tier max per request
_RATE_LIMIT_SLEEP = 1.5      # 1 request/second on free tier


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        from dateutil import parser as du
        dt = du.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _normalize(article: dict[str, Any], query: str) -> RawArticle | None:
    """Convert a GNews API article dict into a RawArticle."""
    url: str = article.get("url", "")
    title: str = (article.get("title") or "").strip()
    if not url or not title:
        return None

    description = (article.get("description") or "").strip()
    full_content = (article.get("content") or "").strip()

    content_parts = [title]
    if description and description.lower() != title.lower():
        content_parts.append(description)
    if full_content and full_content not in (description, title):
        # GNews truncates content with "[x chars]" — remove that
        import re
        full_content = re.sub(r"\s*\[\d+ chars\]\s*$", "", full_content).strip()
        if full_content:
            content_parts.append(full_content)

    content = "\n\n".join(content_parts) or title

    source = article.get("source") or {}
    source_name = source.get("name", "GNews")
    pub_date = _parse_date(article.get("publishedAt"))

    raw_metadata = {
        "source_url": source.get("url", ""),
        "image": article.get("image", ""),
        "query": query,
    }

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=content,
        url=url,
        source="gnews",
        source_name=source_name,
        published_at=pub_date,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata=raw_metadata,
        comments=[],
    )


class GNewsIngester(BaseIngester):
    """Fetches AI/tech news from the GNews.io API."""

    @property
    def source_name(self) -> str:
        return "gnews"

    @property
    def is_enabled(self) -> bool:
        return get_settings().is_gnews_enabled

    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        api_key = settings.gnews_api_key
        if not api_key:
            logger.warning("GNews API key not set")
            return []

        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=20.0) as client:
            for query in _QUERIES:
                await asyncio.sleep(_RATE_LIMIT_SLEEP)
                params = {
                    "token": api_key,
                    "q": query,
                    "lang": "en",
                    "max": _MAX_RESULTS_PER_QUERY,
                    "in": "title,description,content",
                    "sortby": "publishedAt",
                }

                try:
                    resp = await client.get(_BASE_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "GNews HTTP error query='%s': %s (status %d)",
                        query, exc, exc.response.status_code,
                    )
                    continue
                except Exception as exc:
                    logger.warning("GNews request error query='%s': %s", query, exc)
                    continue

                errors = data.get("errors")
                if errors:
                    logger.warning("GNews API error for query='%s': %s", query, errors)
                    continue

                results = data.get("articles") or []
                count = 0
                for item in results:
                    article = _normalize(item, query)
                    if article and article.url not in seen_urls:
                        seen_urls.add(article.url)
                        articles.append(article)
                        count += 1

                logger.debug("GNews query='%s' → %d articles", query, count)

        logger.info("GNews ingestion complete — %d articles", len(articles))
        return articles
