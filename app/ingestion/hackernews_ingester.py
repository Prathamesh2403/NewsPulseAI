"""
Hacker News ingester.

Fetches top stories and top comments using the official HN Firebase API.
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import generate_article_id
from app.schemas.article import RawArticle

logger = get_logger(__name__)

_BASE_URL = "https://hacker-news.firebaseio.com/v0"


def clean_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r'<[^>]+>', '', text)


class HackerNewsIngester(BaseIngester):
    """Fetches top stories from Hacker News."""

    @property
    def source_name(self) -> str:
        return "hackernews"

    @property
    def is_enabled(self) -> bool:
        return True

    async def fetch(self) -> list[RawArticle]:
        articles: list[RawArticle] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(f"{_BASE_URL}/topstories.json")
                resp.raise_for_status()
                story_ids = resp.json()
            except Exception as exc:
                logger.warning("Hacker News request error: %s", exc)
                return articles

            # Fetch top stories
            for story_id in story_ids[:50]:  # Limit to top 50 to avoid too many requests
                try:
                    resp = await client.get(f"{_BASE_URL}/item/{story_id}.json")
                    resp.raise_for_status()
                    story = resp.json()
                except Exception as exc:
                    logger.warning("HN story %s fetch error: %s", story_id, exc)
                    continue

                if not story:
                    continue

                url = story.get("url")
                score = story.get("score", 0)
                
                # Filter: score > 50 and url must exist
                if score <= 50 or not url:
                    continue

                title = story.get("title", "").strip()
                if not title:
                    continue

                # Fetch top 5 comments
                comments: list[str] = []
                kids = story.get("kids", [])[:5]
                for kid_id in kids:
                    try:
                        c_resp = await client.get(f"{_BASE_URL}/item/{kid_id}.json")
                        c_resp.raise_for_status()
                        c_data = c_resp.json()
                        if c_data and c_data.get("type") == "comment" and c_data.get("text"):
                            c_text = clean_html(c_data["text"])
                            comments.append(c_text)
                    except Exception as exc:
                        logger.debug("HN comment %s fetch error: %s", kid_id, exc)

                content_parts = [title]
                if comments:
                    content_parts.append("\n\n--- Community Discussion ---")
                    for i, c in enumerate(comments, 1):
                        content_parts.append(f"Comment {i}: {c}")

                content = "\n".join(content_parts)

                if len(content.split()) < 200:
                    continue

                pub_dt = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc) if story.get("time") else datetime.now(tz=timezone.utc)

                raw_metadata = {
                    "hn_id": story_id,
                    "score": score,
                    "by": story.get("by"),
                    "descendants": story.get("descendants", 0),
                }

                article = RawArticle(
                    id=generate_article_id(url, title),
                    title=title,
                    content=content,
                    url=url,
                    source="hackernews",
                    source_name="Hacker News",
                    published_at=pub_dt,
                    fetched_at=datetime.now(tz=timezone.utc),
                    raw_metadata=raw_metadata,
                    comments=comments,
                )
                articles.append(article)

        logger.info("Hacker News ingestion complete — %d articles", len(articles))
        return articles
