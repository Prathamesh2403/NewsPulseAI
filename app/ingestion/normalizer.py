"""
Normalizer utilities for converting source-specific API responses
into unified ``RawArticle`` schema objects.

Includes a deterministic ID generator and per-source normalization
functions for NYT, Tavily, and Reddit data.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dateutil_parser

from app.core.logging import get_logger
from app.schemas.article import RawArticle

logger = get_logger(__name__)


def generate_article_id(url: str, title: str) -> str:
    """Generate a deterministic article ID from its URL and title.

    Uses SHA-256 to produce a hex digest that uniquely (enough) identifies
    an article across ingestion runs.

    Args:
        url: The article URL.
        title: The article headline / title.

    Returns:
        64-character hex string.
    """
    raw = f"{url}{title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_parse_date(value: Any) -> datetime | None:
    """Attempt to parse a date string into a timezone-aware datetime.

    Returns ``None`` on failure rather than raising, so callers can
    continue gracefully.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = dateutil_parser.parse(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, OverflowError) as exc:
        logger.warning("Failed to parse date '%s': %s", value, exc)
        return None


# ---------------------------------------------------------------------------
# Tavily
# ---------------------------------------------------------------------------

def normalize_tavily_result(result: dict[str, Any]) -> RawArticle:
    """Convert a Tavily search result into a ``RawArticle``.

    Args:
        result: Single result dict from the Tavily SDK response.

    Returns:
        Normalised ``RawArticle`` instance.
    """
    title: str = result.get("title", "Untitled")
    content: str = result.get("content", "")
    url: str = result.get("url", "")
    pub_date = _safe_parse_date(result.get("published_date"))

    raw_metadata: dict[str, Any] = {
        "score": result.get("score"),
    }

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=content or title,
        url=url,
        source="tavily",
        source_name="Tavily Search",
        published_at=pub_date,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata=raw_metadata,
    )


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

def normalize_reddit_post(post: Any) -> RawArticle:
    """Convert a PRAW ``Submission`` object into a ``RawArticle``.

    The Reddit post's ``permalink`` is used to build the canonical URL,
    and ``created_utc`` (Unix timestamp) is converted to a datetime.

    Args:
        post: A ``praw.models.Submission`` instance.

    Returns:
        Normalised ``RawArticle`` instance.
    """
    title: str = getattr(post, "title", "Untitled")
    selftext: str = getattr(post, "selftext", "") or ""
    content = f"{title}\n\n{selftext}" if selftext else title

    permalink: str = getattr(post, "permalink", "")
    url = f"https://reddit.com{permalink}"

    created_utc: float = getattr(post, "created_utc", 0.0)
    pub_date: datetime | None = None
    if created_utc:
        pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc)

    raw_metadata: dict[str, Any] = {
        "score": getattr(post, "score", 0),
        "num_comments": getattr(post, "num_comments", 0),
        "subreddit": str(getattr(post, "subreddit", "")),
        "external_url": getattr(post, "url", ""),
    }

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=content,
        url=url,
        source="reddit",
        source_name=f"r/{raw_metadata['subreddit']}",
        published_at=pub_date,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata=raw_metadata,
    )
