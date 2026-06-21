"""
NewsAPI.ai (EventRegistry) ingester.

Fetches AI/tech news articles using the EventRegistry API.
Docs: https://newsapi.ai/documentation
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

_BASE_URL = "https://eventregistry.org/api/v1/article/getArticles"

_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "LLM large language model",
    "generative AI",
    "OpenAI",
    "robotics AI",
    "AI startup",
    "GPU semiconductor",
    "AI regulation",
]

_ARTICLES_PER_KEYWORD = 20
_RATE_LIMIT_SLEEP = 1.0


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


def _normalize(item: dict[str, Any], keyword: str) -> RawArticle | None:
    """Convert an EventRegistry article result into a RawArticle."""
    url = item.get("url", "")
    title = (item.get("title") or "").strip()
    if not url or not title:
        return None

    body = (item.get("body") or "").strip()
    content = f"{title}\n\n{body}" if body else title

    # Filter: must have >250 words
    if len(content.split()) < 250:
        return None

    # Filter: must have image URL
    image_url = item.get("image") or None
    if not image_url:
        return None

    source_info = item.get("source", {})
    source_name = source_info.get("title", "NewsAPI.ai") if isinstance(source_info, dict) else "NewsAPI.ai"
    pub_date = _parse_date(item.get("dateTimePub"))

    raw_metadata = {
        "newsapi_uri": item.get("uri"),
        "source_uri": source_info.get("uri") if isinstance(source_info, dict) else None,
        "lang": item.get("lang"),
        "keyword": keyword,
        "isDuplicate": item.get("isDuplicate", False),
    }

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=content,
        url=url,
        source="newsapi",
        source_name=source_name,
        published_at=pub_date,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata=raw_metadata,
        image_url=image_url,
    )


class NewsAPIIngester(BaseIngester):
    """Fetches AI/tech articles from NewsAPI.ai (EventRegistry)."""

    @property
    def source_name(self) -> str:
        return "newsapi"

    @property
    def is_enabled(self) -> bool:
        return get_settings().is_newsapi_enabled

    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        api_key = settings.newsapi_key
        if not api_key:
            logger.warning("NewsAPI.ai key not set")
            return []

        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for keyword in _KEYWORDS:
                await asyncio.sleep(_RATE_LIMIT_SLEEP)

                payload = {
                    "action": "getArticles",
                    "keyword": keyword,
                    "sourceLocationUri": "http://en.wikipedia.org/wiki/United_States",
                    "ignoreSourceGroupUri": "paywall/paywalled_sources",
                    "articlesPage": 1,
                    "articlesCount": _ARTICLES_PER_KEYWORD,
                    "articlesSortBy": "date",
                    "resultType": "articles",
                    "dataType": ["news"],
                    "apiKey": api_key,
                }

                try:
                    resp = await client.post(_BASE_URL, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as exc:
                    logger.warning("NewsAPI.ai HTTP error keyword='%s': %s", keyword, exc)
                    continue
                except Exception as exc:
                    logger.warning("NewsAPI.ai request error: %s", exc)
                    continue

                results = (data.get("articles") or {}).get("results") or []

                for item in results:
                    # Skip duplicates flagged by EventRegistry
                    if item.get("isDuplicate", False):
                        continue

                    article = _normalize(item, keyword)
                    if article and article.url not in seen_urls:
                        seen_urls.add(article.url)
                        articles.append(article)

                logger.debug(
                    "NewsAPI.ai keyword='%s' → %d results, %d valid",
                    keyword, len(results), len([a for a in [_normalize(i, keyword) for i in results] if a]),
                )

        logger.info("NewsAPI.ai ingestion complete — %d articles", len(articles))
        return articles
