"""
Dev.to ingester.

Fetches AI articles from dev.to API.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import generate_article_id
from app.schemas.article import RawArticle

logger = get_logger(__name__)

_BASE_URL = "https://dev.to/api/articles"


class DevToIngester(BaseIngester):
    """Fetches AI articles from Dev.to."""

    @property
    def source_name(self) -> str:
        return "devto"

    @property
    def is_enabled(self) -> bool:
        return True

    async def fetch(self) -> list[RawArticle]:
        articles: list[RawArticle] = []

        params = {
            "tag": "ai",
            "per_page": 20,
            "top": 1,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                items = resp.json()
            except Exception as exc:
                logger.warning("Dev.to request error: %s", exc)
                return articles

            for item in items:
                try:
                    reactions = item.get("public_reactions_count", 0)
                    if reactions <= 10:
                        continue

                    url = item.get("url")
                    title = item.get("title", "").strip()
                    if not url or not title:
                        continue
                        
                    # Dev.to list API doesn't return full content, just description.
                    # We might need to fetch the individual article by ID to get the full body_markdown.
                    article_id = item.get("id")
                    if not article_id:
                        continue

                    # Fetch full article to get body_markdown
                    try:
                        detail_resp = await client.get(f"{_BASE_URL}/{article_id}")
                        detail_resp.raise_for_status()
                        detail_item = detail_resp.json()
                        content = detail_item.get("body_markdown", "") or item.get("description", "")
                    except Exception as exc:
                        logger.warning("Dev.to fetch article %s error: %s", article_id, exc)
                        content = item.get("description", "")

                    if len(content.split()) < 200:
                        continue

                    username = item.get("user", {}).get("username", "unknown")
                    source_name = f"DEV/@{username}"

                    pub_date_str = item.get("published_at")
                    try:
                        from dateutil import parser as du
                        pub_dt = du.parse(pub_date_str)
                    except Exception:
                        pub_dt = datetime.now(tz=timezone.utc)

                    raw_metadata = {
                        "devto_id": article_id,
                        "reactions": reactions,
                        "comments_count": item.get("comments_count", 0),
                        "tags": item.get("tag_list", []),
                    }

                    article = RawArticle(
                        id=generate_article_id(url, title),
                        title=title,
                        content=content,
                        url=url,
                        source="devto",
                        source_name=source_name,
                        published_at=pub_dt,
                        fetched_at=datetime.now(tz=timezone.utc),
                        raw_metadata=raw_metadata,
                        comments=[],
                        image_url=item.get("cover_image") or None,
                    )
                    articles.append(article)
                    
                    # Be nice to the API
                    await asyncio.sleep(0.5)

                except Exception as exc:
                    logger.warning("Dev.to parse item error: %s", exc)

        logger.info("Dev.to ingestion complete — %d articles", len(articles))
        return articles
