"""
RSS ingester.

Fetches AI/tech news from multiple RSS feeds.
"""

import asyncio
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

import httpx

from app.core.logging import get_logger
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import generate_article_id
from app.schemas.article import RawArticle

logger = get_logger(__name__)

_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Ars Technica AI": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "Hacker News Best": "https://hnrss.org/best?points=100",
    "Hacker News AI": "https://hnrss.org/newest?q=AI+LLM+machine+learning&points=50",
    "Papers With Code": "https://paperswithcode.com/latest.xml",
}


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class RSSIngester(BaseIngester):
    """Fetches top stories from RSS feeds."""

    @property
    def source_name(self) -> str:
        return "rss"

    @property
    def is_enabled(self) -> bool:
        return True

    async def fetch(self) -> list[RawArticle]:
        articles: list[RawArticle] = []

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for feed_name, url in _FEEDS.items():
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    
                    import feedparser
                    feed = await asyncio.to_thread(feedparser.parse, resp.text)
                    
                    for entry in feed.entries[:10]:
                        link = entry.get("link", "")
                        title = _strip_html(entry.get("title", "Untitled"))
                        if not link or not title:
                            continue

                        summary = _strip_html(entry.get("summary", ""))
                        content_raw = _strip_html(entry.get("content", [{"value": ""}])[0].get("value", ""))

                        # Combine parts to form content
                        content_parts = [title]
                        if summary and summary.lower() != title.lower():
                            content_parts.append(summary)
                        if content_raw and content_raw.lower() not in (title.lower(), summary.lower()):
                            content_parts.append(content_raw)
                            
                        content = "\n\n".join(content_parts)

                        # Filter: skip articles with < 200 words in content
                        if len(content.split()) < 200:
                            continue

                        pub_struct = entry.get("published_parsed")
                        pub_dt = datetime(*pub_struct[:6], tzinfo=timezone.utc) if pub_struct else datetime.now(tz=timezone.utc)

                        raw_metadata = {
                            "feed_name": feed_name,
                            "author": _strip_html(entry.get("author", "")),
                        }

                        article = RawArticle(
                            id=generate_article_id(link, title),
                            title=title,
                            content=content,
                            url=link,
                            source="rss",
                            source_name=feed_name,
                            published_at=pub_dt,
                            fetched_at=datetime.now(tz=timezone.utc),
                            raw_metadata=raw_metadata,
                            comments=[],
                        )
                        articles.append(article)
                        
                except Exception as exc:
                    logger.warning("Error fetching RSS feed %s: %s", feed_name, exc)

        logger.info("RSS ingestion complete — %d articles", len(articles))
        return articles
