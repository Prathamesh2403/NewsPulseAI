"""
Reddit Comment Enrichment Script
=================================
Fetches comments for Reddit articles already in the DB that have
empty comments (either comment_count=0 or comments_pending=true).

Run this script independently, any time after a cooldown period
(15-20 minutes after the main pipeline ran), to backfill comments.

Usage:
    python enrich_comments.py [--limit N] [--subreddit r/NAME] [--dry-run]

The script:
1. Queries DB for Reddit articles with no comments
2. Fetches comment RSS for each post (with polite delays + backoff)
3. Updates both the comments column AND raw_metadata in-place
4. Also re-upserts the article content to include the Community Discussion block
"""

import asyncio
import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from html import unescape
from typing import Any

import httpx

sys.path.insert(0, ".")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("enrich_comments")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_MAX_COMMENTS = 10
_COMMENT_DELAY = 5.0          # seconds between posts
_BACKOFF_ON_429 = [20, 45, 90, 180]   # escalating waits on rate limits


# ---------------------------------------------------------------------------
# HTML cleanup
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    clean = re.sub(r"submitted\s+by\s+/u/\S+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[(link|comments|score hidden|deleted|removed)\]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


# ---------------------------------------------------------------------------
# Comment fetching
# ---------------------------------------------------------------------------

async def fetch_comments(
    post_id: str,
    subreddit: str,
    client: httpx.AsyncClient,
) -> list[str]:
    """Fetch comments via per-post RSS. Returns [] if still rate-limited."""
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/.rss"

    for attempt, backoff in enumerate(_BACKOFF_ON_429):
        try:
            resp = await client.get(url, timeout=25.0)
        except Exception as exc:
            logger.warning("Request error for %s: %s", post_id, exc)
            return []

        if resp.status_code == 429:
            if attempt < len(_BACKOFF_ON_429) - 1:
                logger.warning(
                    "  429 on %s — waiting %ds before retry %d...",
                    post_id, backoff, attempt + 2,
                )
                await asyncio.sleep(backoff)
                continue
            else:
                logger.warning("  %s — still rate-limited after all retries. Skipping.", post_id)
                return []

        if resp.status_code != 200:
            logger.debug("  %s — status %d, no comments", post_id, resp.status_code)
            return []

        import feedparser
        feed = feedparser.parse(resp.text)
        comments: list[str] = []

        for entry in feed.entries:
            link = entry.get("link", "")
            after = link.split("/comments/")[-1] if "/comments/" in link else ""
            segments = [s for s in after.split("/") if s]
            if len(segments) <= 2:
                continue  # skip OP post entry

            body = _strip_html(entry.get("summary", "") or "")
            if body and len(body) > 10:
                comments.append(body)
                if len(comments) >= _MAX_COMMENTS:
                    break

        return comments

    return []


# ---------------------------------------------------------------------------
# Content rebuilding
# ---------------------------------------------------------------------------

def _rebuild_content(original_content: str, comments: list[str]) -> str:
    """Add/replace the Community Discussion block in article content."""
    # Remove any existing Community Discussion block
    base = re.sub(r"\n\n--- Community Discussion ---.*", "", original_content, flags=re.DOTALL).strip()

    if not comments:
        return base

    parts = [base, "\n\n--- Community Discussion ---"]
    for i, c in enumerate(comments[:5], 1):
        truncated = c[:400] + "..." if len(c) > 400 else c
        parts.append(f"Comment {i}: {truncated}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main enrichment loop
# ---------------------------------------------------------------------------

async def run_enrichment(limit: int = 100, subreddit_filter: str = "", dry_run: bool = False):
    from app.db.session import async_session_factory
    from sqlalchemy import text

    # Query Reddit articles with no comments
    query = """
        SELECT id, url, title, content, raw_metadata
        FROM articles
        WHERE source = 'reddit'
          AND (
              comments IS NULL
              OR jsonb_array_length(comments::jsonb) = 0
          )
    """
    if subreddit_filter:
        sub = subreddit_filter.lstrip("r/")
        query += f" AND raw_metadata->>'subreddit' = '{sub}'"
    query += f" ORDER BY published_at DESC LIMIT {limit}"

    async with async_session_factory() as session:
        result = await session.execute(text(query))
        rows = result.fetchall()

    logger.info(
        "Found %d Reddit articles with no comments%s",
        len(rows),
        f" (filter: r/{subreddit_filter.lstrip('r/')})" if subreddit_filter else "",
    )

    if not rows:
        logger.info("Nothing to enrich — all Reddit articles already have comments!")
        return

    if dry_run:
        logger.info("[DRY RUN] Would enrich %d articles", len(rows))
        for row in rows[:5]:
            meta = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
            logger.info("  - %s (post_id=%s, r/%s)", row[2][:60], meta.get("post_id"), meta.get("subreddit"))
        return

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    success_count = 0
    skip_count = 0
    consecutive_failures = 0

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for idx, row in enumerate(rows):
            art_id, url, title, content, raw_meta_raw = row
            meta = raw_meta_raw if isinstance(raw_meta_raw, dict) else json.loads(raw_meta_raw or "{}")

            post_id = meta.get("post_id", "")
            subreddit = meta.get("subreddit", "")

            if not post_id or not subreddit:
                logger.debug("Skipping %s — missing post_id or subreddit", art_id[:16])
                skip_count += 1
                continue

            # Stop if too many consecutive failures (Reddit may be blocking)
            if consecutive_failures >= 5:
                logger.error(
                    "5 consecutive failures — Reddit is rate-limiting. "
                    "Wait 15+ minutes and re-run. %d articles remain.",
                    len(rows) - idx,
                )
                break

            if idx > 0:
                await asyncio.sleep(_COMMENT_DELAY)

            logger.info(
                "[%d/%d] Fetching comments for '%s...' (r/%s, post=%s)",
                idx + 1, len(rows), title[:50], subreddit, post_id,
            )

            comments = await fetch_comments(post_id, subreddit, client)

            if not comments:
                consecutive_failures += 1
                logger.info("  -> No comments retrieved (rate-limited or empty post)")
                continue

            consecutive_failures = 0
            logger.info("  -> Got %d comments ✓", len(comments))

            # Rebuild content with Community Discussion block
            new_content = _rebuild_content(content or "", comments)

            # Update raw_metadata
            meta["comment_count"] = len(comments)
            meta["top_comments"] = comments[:3]
            meta["comments_pending"] = False

            # Write back to DB
            async with async_session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE articles
                        SET comments = :comments,
                            content = :content,
                            raw_metadata = :meta
                        WHERE id = :id
                    """),
                    {
                        "comments": json.dumps(comments),
                        "content": new_content,
                        "meta": json.dumps(meta),
                        "id": art_id,
                    }
                )
                await session.commit()

            success_count += 1

    logger.info(
        "\n=== Enrichment complete ===\n"
        "  Enriched: %d articles\n"
        "  Skipped:  %d articles (no post_id)\n"
        "  Failed:   %d articles (rate-limited)\n"
        "  Remaining with no comments: %d",
        success_count,
        skip_count,
        consecutive_failures,
        len(rows) - success_count - skip_count,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich Reddit articles with comments")
    parser.add_argument("--limit", type=int, default=100, help="Max articles to process")
    parser.add_argument("--subreddit", type=str, default="", help="Filter by subreddit (e.g. r/OpenAI)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    asyncio.run(run_enrichment(
        limit=args.limit,
        subreddit_filter=args.subreddit,
        dry_run=args.dry_run,
    ))
