"""
ApiTube ingester.

Fetches technology news articles using the ApiTube API.
Docs: https://apitube.io/docs
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

_BASE_URL = "https://api.apitube.io/v1/news/everything"

# Multiple category/keyword searches to maximize coverage
_SEARCHES = [
    {"title": "artificial intelligence"},
    {"title": "machine learning"},
    {"title": "LLM"},
    {"title": "AI startup"},
    {"title": "AI research"},
]

_LIMIT_PER_SEARCH = 30
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


def _normalize(item: dict[str, Any]) -> RawArticle | None:
    """Convert an ApiTube article result into a RawArticle."""
    url = item.get("url", "")
    title = (item.get("title") or "").strip()
    if not url or not title:
        return None

    # Construct content from summary instead of body (body is paywalled on free tier)
    summary_list = item.get("summary", [])
    body = " ".join(s.get("sentence", "") for s in summary_list if isinstance(s, dict)).strip()
    
    content = f"{title}\n\n{body}" if body else title

    # Filter: must have >250 words
    if len(content.split()) < 250:
        return None

    # Filter: must have image URL
    image_url = item.get("image_url") or item.get("image") or None
    if not image_url:
        return None

    source_info = item.get("source", {})
    source_name = source_info.get("name", "ApiTube") if isinstance(source_info, dict) else "ApiTube"
    pub_date = _parse_date(item.get("published_at"))

    raw_metadata = {
        "apitube_id": item.get("id"),
        "source_url": source_info.get("url") if isinstance(source_info, dict) else None,
        "language": item.get("language"),
    }

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=content,
        url=url,
        source="apitube",
        source_name=source_name,
        published_at=pub_date,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata=raw_metadata,
        image_url=image_url,
    )


class ApiTubeIngester(BaseIngester):
    """Fetches tech/AI articles from the ApiTube API."""

    @property
    def source_name(self) -> str:
        return "apitube"

    @property
    def is_enabled(self) -> bool:
        return get_settings().is_apitube_enabled

    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        api_key = settings.apitube_api_key
        if not api_key:
            logger.warning("ApiTube API key not set")
            return []

        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for search in _SEARCHES:
                await asyncio.sleep(_RATE_LIMIT_SLEEP)

                headers = {
                    "X-API-Key": api_key
                }

                params = {
                    "title": search["title"],
                    "language.code": "en",
                    "is_duplicate": "0",
                    "sort.by": "published_at",
                    "sort.order": "desc",
                    "per_page": _LIMIT_PER_SEARCH,
                }

                try:
                    resp = await client.get(_BASE_URL, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as exc:
                    logger.warning("ApiTube HTTP error title='%s': %s", search["title"], exc)
                    continue
                except Exception as exc:
                    logger.warning("ApiTube request error: %s", exc)
                    continue

                # Use results as per the correct ApiTube schema
                results = data.get("results", [])
                if not isinstance(results, list):
                    results = []

                for item in results:
                    article = _normalize(item)
                    if article and article.url not in seen_urls:
                        seen_urls.add(article.url)
                        articles.append(article)

                logger.debug(
                    "ApiTube title='%s' -> %d results",
                    search["title"], len(results),
                )

        logger.info("ApiTube ingestion complete — %d articles", len(articles))
        return articles
