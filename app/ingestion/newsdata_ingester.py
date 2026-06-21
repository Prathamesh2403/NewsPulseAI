"""
NewsData.io ingester.

Fetches AI/tech news from the NewsData.io API (https://newsdata.io).
Supports round-robin across multiple API keys.
Free tier: 200 requests/day per key, 10 results/page.
"""

import asyncio
import itertools
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import generate_article_id
from app.schemas.article import RawArticle

logger = get_logger(__name__)

_BASE_URL = "https://newsdata.io/api/1/news"

# AI/tech search queries
_QUERIES = [
    "artificial intelligence",
    "large language model",
    "generative AI",
    "OpenAI GPT",
    "AI robotics",
    "AI regulation policy",
    "machine learning research",
    "AI startup funding",
    "GPU semiconductor chip",
    "tech industry news",
]

_CATEGORIES = "technology,science"
_MAX_PAGES_PER_QUERY = 3
_RATE_LIMIT_SLEEP = 1.5


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


def _normalize(item: dict[str, Any], query: str) -> RawArticle | None:
    """Convert a NewsData.io result item into a RawArticle."""
    url: str = item.get("link", "")
    title: str = item.get("title", "").strip()
    if not url or not title:
        return None

    # Build content from description + content
    description = (item.get("description") or "").strip()
    full_content = (item.get("content") or "").strip()
    content_parts = [title]
    if description and description.lower() != title.lower():
        content_parts.append(description)
    if full_content and full_content not in (description, title):
        content_parts.append(full_content)
    content = "\n\n".join(content_parts) or title

    # Filter: must have >250 words
    if len(content.split()) < 250:
        logger.debug("Skipping NewsData.io article (< 250 words): %s", url)
        return None

    # Filter: must have image URL
    image_url = item.get("image_url") or None
    if not image_url:
        logger.debug("Skipping NewsData.io article (no image): %s", url)
        return None

    source_id = item.get("source_id", "newsdata")
    source_name = item.get("source_name", source_id) or source_id
    pub_date = _parse_date(item.get("pubDate"))

    raw_metadata = {
        "source_id": source_id,
        "creator": item.get("creator"),
        "keywords": item.get("keywords") or [],
        "country": item.get("country"),
        "language": item.get("language"),
        "category": item.get("category"),
        "query": query,
    }

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=content,
        url=url,
        source="newsdata",
        source_name=source_name,
        published_at=pub_date,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata=raw_metadata,
        image_url=image_url,
    )


class NewsdataIngester(BaseIngester):
    """Fetches AI/tech articles from the NewsData.io API with round-robin keys."""

    @property
    def source_name(self) -> str:
        return "newsdata"

    @property
    def is_enabled(self) -> bool:
        return get_settings().is_newsdata_enabled

    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        keys = settings.all_newsdata_keys
        if not keys:
            logger.warning("NewsData.io API key not set")
            return []

        # Round-robin key iterator
        key_cycle = itertools.cycle(keys)

        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=20.0) as client:
            for query in _QUERIES:
                next_page: str | None = None
                for page_num in range(_MAX_PAGES_PER_QUERY):
                    await asyncio.sleep(_RATE_LIMIT_SLEEP)
                    api_key = next(key_cycle)

                    params: dict[str, Any] = {
                        "apikey": api_key,
                        "q": query,
                        "language": "en",
                        "category": _CATEGORIES,
                        "size": 10,
                    }
                    if next_page:
                        params["page"] = next_page

                    try:
                        resp = await client.get(_BASE_URL, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                    except httpx.HTTPStatusError as exc:
                        logger.warning(
                            "NewsData.io HTTP error query='%s' page=%d: %s",
                            query, page_num, exc,
                        )
                        break
                    except Exception as exc:
                        logger.warning("NewsData.io request error: %s", exc)
                        break

                    if data.get("status") != "success":
                        logger.warning(
                            "NewsData.io non-success response: %s",
                            data.get("message", "unknown"),
                        )
                        break

                    results = data.get("results") or []
                    for item in results:
                        article = _normalize(item, query)
                        if article and article.url not in seen_urls:
                            seen_urls.add(article.url)
                            articles.append(article)

                    next_page = data.get("nextPage")
                    if not next_page or not results:
                        break

                    logger.debug(
                        "NewsData.io query='%s' page=%d → %d items",
                        query, page_num, len(results),
                    )

        logger.info("NewsData.io ingestion complete — %d articles", len(articles))
        return articles
