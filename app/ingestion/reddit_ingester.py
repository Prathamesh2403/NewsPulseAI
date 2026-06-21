"""
Reddit ingester using RSS feeds (no API key required).

Fetches hot posts from curated AI/tech subreddits via Reddit's public
RSS feed URLs using feedparser. Comments are fetched via each post's
per-post RSS endpoint (/comments/<id>/.rss).

Key design decisions:
- RSS feeds fetched SEQUENTIALLY with delays to avoid IP rate-limiting.
- Comment fetching uses EXPONENTIAL BACKOFF on 429: backs off up to 5
  minutes, marks remaining posts as "pending" rather than silently dropping.
- Posts with comment_count=0 can be enriched later via enrich_comments.py.
- All 5 default subreddits are always attempted; 429 on subreddit RSS
  triggers a longer backoff before the next one.

This ingester is ALWAYS enabled — no credentials needed.
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_SUBREDDITS: list[str] = [
    "artificial",
    "MachineLearning",
    "OpenAI",
    "technology",
    "singularity",
]

_POSTS_PER_SUBREDDIT: int = 10       # 10 posts per subreddit = 50 total
_MAX_COMMENTS: int = 10              # top-k comments per post
_RSS_DELAY_SECS: float = 6.0        # delay between subreddit RSS fetches
_COMMENT_DELAY_SECS: float = 4.0    # delay between comment RSS fetches

# Backoff schedule (seconds) when we get 429 on comment RSS
# [15, 30, 60, 120, 300] — we try up to 5 times before giving up on that post
_BACKOFF_SCHEDULE: list[int] = [15, 30, 60, 120, 300]

# After this many consecutive 429s in a row, stop fetching comments for
# remaining posts (they'll be filled in by enrich_comments.py later)
_MAX_CONSECUTIVE_429 = 3

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags, decode entities, strip Reddit boilerplate."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    clean = re.sub(r"submitted\s+by\s+/u/\S+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[(link|comments|score hidden|deleted|removed)\]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


# ---------------------------------------------------------------------------
# Subreddit RSS fetch (with 429 backoff on the subreddit itself)
# ---------------------------------------------------------------------------

async def _fetch_subreddit_rss(
    subreddit: str,
    client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    """Fetch hot RSS for a subreddit. Returns [] on failure."""
    url = f"https://www.reddit.com/r/{subreddit}/hot/.rss"

    for attempt, backoff in enumerate([0, 20, 45]):
        if backoff > 0:
            logger.info("Retrying r/%s RSS in %ds (attempt %d)...", subreddit, backoff, attempt + 1)
            await asyncio.sleep(backoff)
        try:
            resp = await client.get(url, timeout=25.0)
            if resp.status_code == 429:
                if attempt < 2:
                    continue   # retry with longer backoff
                logger.warning("r/%s RSS rate-limited (429) after %d attempts — skipping", subreddit, attempt + 1)
                return []
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP error fetching r/%s RSS: %s", subreddit, exc)
            return []
        except Exception as exc:
            logger.warning("Error fetching r/%s RSS: %s", subreddit, exc)
            return []

        import feedparser
        feed = await asyncio.to_thread(feedparser.parse, resp.text)
        entries = []
        for entry in feed.entries[:_POSTS_PER_SUBREDDIT]:
            link: str = entry.get("link", "")
            title: str = _strip_html(entry.get("title", "Untitled"))
            summary: str = _strip_html(entry.get("summary", ""))
            pub_struct = entry.get("published_parsed")
            pub_dt = datetime(*pub_struct[:6], tzinfo=timezone.utc) if pub_struct else datetime.now(tz=timezone.utc)
            post_id = ""
            parts = link.split("/comments/")
            if len(parts) > 1:
                post_id = parts[1].split("/")[0]
            entries.append({
                "title": title, "link": link, "summary": summary,
                "published": pub_dt,
                "author": _strip_html(entry.get("author", "")),
                "post_id": post_id, "subreddit": subreddit,
            })

        logger.info("r/%s: fetched %d posts", subreddit, len(entries))
        return entries

    return []


# ---------------------------------------------------------------------------
# Comment RSS fetch (with exponential backoff)
# ---------------------------------------------------------------------------

async def _fetch_comments_rss(
    post_id: str,
    subreddit: str,
    client: httpx.AsyncClient,
) -> tuple[list[str], bool]:
    """Fetch comments via the post's RSS feed.

    Returns:
        (comments_list, success) — success=False means rate-limited/failed.
    """
    if not post_id:
        return [], True   # no post_id, not an error

    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/.rss"

    for attempt, backoff in enumerate(_BACKOFF_SCHEDULE):
        try:
            resp = await client.get(url, timeout=25.0)
        except Exception as exc:
            logger.debug("Comment RSS request error for %s: %s", post_id, exc)
            return [], False

        if resp.status_code == 429:
            if attempt < len(_BACKOFF_SCHEDULE) - 1:
                logger.warning(
                    "Comment RSS 429 for post %s — waiting %ds (attempt %d/%d)",
                    post_id, backoff, attempt + 1, len(_BACKOFF_SCHEDULE),
                )
                await asyncio.sleep(backoff)
                continue
            else:
                logger.warning("Comment RSS persistently rate-limited for post %s — giving up", post_id)
                return [], False

        if resp.status_code != 200:
            logger.debug("Comment RSS status %d for post %s", resp.status_code, post_id)
            return [], True   # not a rate limit — just empty/missing

        import feedparser
        feed = await asyncio.to_thread(feedparser.parse, resp.text)
        comments: list[str] = []

        for entry in feed.entries:
            entry_link: str = entry.get("link", "")
            after = entry_link.split("/comments/")[-1] if "/comments/" in entry_link else ""
            segments = [s for s in after.split("/") if s]
            if len(segments) <= 2:
                continue   # OP post entry — skip

            body_raw = entry.get("summary", "") or ""
            body = _strip_html(body_raw)
            if body and len(body) > 10:
                comments.append(body)
                if len(comments) >= _MAX_COMMENTS:
                    break

        logger.debug("Post %s: %d comments fetched", post_id, len(comments))
        return comments, True

    return [], False


# ---------------------------------------------------------------------------
# Article assembly
# ---------------------------------------------------------------------------

def _build_content(entry: dict, comments: list[str]) -> str:
    parts = [entry["title"]]
    summary = entry.get("summary", "").strip()
    if summary and summary.lower() != entry["title"].lower():
        parts.append(f"\n{summary}")
    if comments:
        parts.append("\n\n--- Community Discussion ---")
        for i, c in enumerate(comments[:5], 1):
            truncated = c[:400] + "..." if len(c) > 400 else c
            parts.append(f"Comment {i}: {truncated}")
    return "\n".join(parts)


def _to_raw_article(entry: dict, comments: list[str]) -> RawArticle:
    title = entry["title"]
    url = entry["link"]
    subreddit = entry["subreddit"]
    pub_dt = entry["published"]

    return RawArticle(
        id=generate_article_id(url, title),
        title=title,
        content=_build_content(entry, comments),
        url=url,
        source="reddit",
        source_name=f"r/{subreddit}",
        published_at=pub_dt,
        fetched_at=datetime.now(tz=timezone.utc),
        raw_metadata={
            "subreddit": subreddit,
            "author": entry.get("author", ""),
            "post_id": entry.get("post_id", ""),
            "comment_count": len(comments),
            "top_comments": comments[:3],
            "comments_pending": False,
        },
        comments=comments,
    )


# ---------------------------------------------------------------------------
# Main ingester class
# ---------------------------------------------------------------------------

class RedditRSSIngester(BaseIngester):
    """Fetches hot posts + comments from AI/tech subreddits via RSS.

    Subreddit feeds are fetched sequentially. Comments use exponential
    backoff on 429. If Reddit rate-limits persist, posts are stored without
    comments and flagged for the enrichment script to fill in later.
    """

    def __init__(
        self,
        subreddits: list[str] | None = None,
        fetch_comments: bool = True,
    ) -> None:
        self._subreddits = subreddits or _DEFAULT_SUBREDDITS
        self._fetch_comments = fetch_comments

    @property
    def source_name(self) -> str:
        return "reddit"

    @property
    def is_enabled(self) -> bool:
        return True   # RSS always available

    async def fetch(self) -> list[RawArticle]:
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        articles: list[RawArticle] = []

        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:

            # ── Phase 1: Fetch all subreddit feeds (sequential) ──────────
            all_entries: list[dict] = []
            for i, sub in enumerate(self._subreddits):
                if i > 0:
                    logger.info("Waiting %ss before next subreddit...", _RSS_DELAY_SECS)
                    await asyncio.sleep(_RSS_DELAY_SECS)
                entries = await _fetch_subreddit_rss(sub, client)
                all_entries.extend(entries)

            logger.info("Collected %d posts from %d subreddits", len(all_entries), len(self._subreddits))

            if not all_entries:
                return []

            # ── Phase 2: Fetch comments (sequential + smart 429 handling) ─
            if self._fetch_comments:
                logger.info("Fetching comments for %d posts (with backoff on 429)...", len(all_entries))
                await asyncio.sleep(5.0)   # brief cooldown after RSS phase

            consecutive_429s = 0
            total_comments = 0

            for idx, entry in enumerate(all_entries):
                try:
                    comments: list[str] = []

                    if self._fetch_comments and entry.get("post_id"):
                        # If we've hit too many consecutive 429s, stop fetching comments
                        # for remaining posts — they'll be stored as pending
                        if consecutive_429s >= _MAX_CONSECUTIVE_429:
                            logger.warning(
                                "%d consecutive 429s — storing remaining %d posts without comments. "
                                "Run enrich_comments.py later to backfill.",
                                consecutive_429s,
                                len(all_entries) - idx,
                            )
                            # Build articles without comments for the rest
                            for remaining in all_entries[idx:]:
                                try:
                                    art = _to_raw_article(remaining, [])
                                    art.raw_metadata["comments_pending"] = True
                                    articles.append(art)
                                except Exception:
                                    pass
                            break

                        if idx > 0:
                            await asyncio.sleep(_COMMENT_DELAY_SECS)

                        comments, success = await _fetch_comments_rss(
                            entry["post_id"],
                            entry["subreddit"],
                            client,
                        )

                        if not success:
                            consecutive_429s += 1
                            entry_article = _to_raw_article(entry, [])
                            entry_article.raw_metadata["comments_pending"] = True
                            articles.append(entry_article)
                            continue
                        else:
                            consecutive_429s = 0  # reset on success
                            total_comments += len(comments)

                    article = _to_raw_article(entry, comments)
                    articles.append(article)

                except Exception as exc:
                    logger.warning("Failed building article for %s: %s", entry.get("link", "?"), exc)

            logger.info(
                "Reddit ingestion done: %d articles, %d comments total",
                len(articles), total_comments,
            )

        return articles


# Backward-compat alias
RedditIngester = RedditRSSIngester
