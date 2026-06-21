"""
Community pipeline — fetches discussions from HN, Reddit, DevTo
and stores them as CommunityComment rows + ChromaDB embeddings.

Completely separate from the news article pipeline.
"""

import asyncio
import re
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select

from app.db.models import CommunityComment
from app.db.session import async_session_factory
from app.db.vector_store import get_community_vector_store
from app.processing.classifier import classify_article
from app.processing.embedder import generate_embeddings

logger = logging.getLogger(__name__)


def _clean_html(text: str) -> str:
    """Strip HTML tags."""
    return re.sub(r'<[^>]+>', '', text)


# ---------------------------------------------------------------------------
# Hacker News
# ---------------------------------------------------------------------------

async def _fetch_hackernews_comments() -> list[dict[str, Any]]:
    """Fetch top HN stories and their top comments."""
    comments: list[dict[str, Any]] = []
    base = "https://hacker-news.firebaseio.com/v0"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(f"{base}/topstories.json")
            resp.raise_for_status()
            story_ids = resp.json()[:50]
        except Exception as exc:
            logger.warning("HN top stories fetch error: %s", exc)
            return comments

        for story_id in story_ids:
            try:
                resp = await client.get(f"{base}/item/{story_id}.json")
                resp.raise_for_status()
                story = resp.json()
            except Exception:
                continue

            if not story or story.get("score", 0) < 30:
                continue

            story_title = story.get("title", "")
            story_url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            story_time = story.get("time", 0)
            pub_dt = datetime.fromtimestamp(story_time, tz=timezone.utc) if story_time else None

            kids = story.get("kids", [])[:5]
            for kid_id in kids:
                try:
                    c_resp = await client.get(f"{base}/item/{kid_id}.json")
                    c_resp.raise_for_status()
                    c_data = c_resp.json()
                except Exception:
                    continue

                if not c_data or c_data.get("type") != "comment" or not c_data.get("text"):
                    continue

                body = _clean_html(c_data["text"])
                if len(body.split()) < 10:
                    continue

                comments.append({
                    "platform": "hackernews",
                    "username": c_data.get("by", "anonymous"),
                    "body": body[:2000],
                    "url": f"https://news.ycombinator.com/item?id={kid_id}",
                    "upvotes": 0,  # HN doesn't expose comment scores
                    "published_at": pub_dt,
                    "context_title": story_title,
                })

    logger.info("HN community fetch: %d comments", len(comments))
    return comments


# ---------------------------------------------------------------------------
# Reddit (RSS — no auth needed)
# ---------------------------------------------------------------------------

_REDDIT_FEEDS = [
    "https://www.reddit.com/r/artificial/hot.json?limit=25",
    "https://www.reddit.com/r/MachineLearning/hot.json?limit=25",
    "https://www.reddit.com/r/technology/hot.json?limit=25",
    "https://www.reddit.com/r/OpenAI/hot.json?limit=15",
]


async def _fetch_reddit_comments() -> list[dict[str, Any]]:
    """Fetch Reddit posts as community comments."""
    comments: list[dict[str, Any]] = []

    headers = {"User-Agent": "news_bot:v1.0 (by /u/newsbot_ai)"}

    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        for feed_url in _REDDIT_FEEDS:
            await asyncio.sleep(2.0)  # Reddit rate limit
            try:
                resp = await client.get(feed_url)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("Reddit feed error %s: %s", feed_url, exc)
                continue

            posts = data.get("data", {}).get("children", [])
            for post_data in posts:
                post = post_data.get("data", {})
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                body = f"{title}\n\n{selftext}".strip() if selftext else title

                if len(body.split()) < 15:
                    continue

                permalink = post.get("permalink", "")
                pub_dt = None
                if post.get("created_utc"):
                    pub_dt = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)

                comments.append({
                    "platform": "reddit",
                    "username": post.get("author", "anonymous"),
                    "body": body[:2000],
                    "url": f"https://reddit.com{permalink}" if permalink else "",
                    "upvotes": post.get("score", 0),
                    "published_at": pub_dt,
                    "context_title": title,
                })

    logger.info("Reddit community fetch: %d comments", len(comments))
    return comments


# ---------------------------------------------------------------------------
# Dev.to
# ---------------------------------------------------------------------------

async def _fetch_devto_comments() -> list[dict[str, Any]]:
    """Fetch recent Dev.to articles as community comments."""
    comments: list[dict[str, Any]] = []
    tags = ["ai", "machinelearning", "llm", "openai", "python"]

    async with httpx.AsyncClient(timeout=20.0) as client:
        for tag in tags:
            await asyncio.sleep(1.0)
            try:
                resp = await client.get(
                    "https://dev.to/api/articles",
                    params={"tag": tag, "per_page": 15, "top": 7},
                )
                resp.raise_for_status()
                articles = resp.json()
            except Exception as exc:
                logger.warning("Dev.to fetch error tag='%s': %s", tag, exc)
                continue

            for article in articles:
                title = article.get("title", "")
                description = article.get("description", "")
                body = f"{title}\n\n{description}".strip()

                if len(body.split()) < 10:
                    continue

                pub_date = None
                if article.get("published_at"):
                    try:
                        from dateutil import parser as du
                        pub_date = du.parse(article["published_at"])
                    except Exception:
                        pass

                comments.append({
                    "platform": "devto",
                    "username": (article.get("user") or {}).get("username", "anonymous"),
                    "body": body[:2000],
                    "url": article.get("url", ""),
                    "upvotes": article.get("positive_reactions_count", 0),
                    "published_at": pub_date,
                    "context_title": title,
                })

    logger.info("Dev.to community fetch: %d comments", len(comments))
    return comments


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_community_pipeline() -> int:
    """Fetch community discussions and store in Postgres + ChromaDB.

    Returns:
        Number of new comments stored.
    """
    logger.info("Starting community ingestion pipeline...")

    # 1. Fetch from all sources concurrently
    hn_task = _fetch_hackernews_comments()
    reddit_task = _fetch_reddit_comments()
    devto_task = _fetch_devto_comments()
    hn_comments, reddit_comments, devto_comments = await asyncio.gather(
        hn_task, reddit_task, devto_task, return_exceptions=False
    )

    all_comments = hn_comments + reddit_comments + devto_comments
    logger.info("Total community comments fetched: %d", len(all_comments))

    if not all_comments:
        return 0

    # 2. Deduplicate by body hash
    seen: set[str] = set()
    unique_comments: list[dict[str, Any]] = []
    for c in all_comments:
        body_hash = hash(c["body"][:200])
        if body_hash not in seen:
            seen.add(body_hash)
            unique_comments.append(c)

    logger.info("Unique comments after dedup: %d", len(unique_comments))

    # 3. Classify topics for each comment
    for c in unique_comments:
        try:
            category = classify_article(c.get("context_title", ""), c["body"])
            c["topic_tags"] = [category] if category != "Other" else []
        except Exception:
            c["topic_tags"] = []

    # 4. Store in Postgres
    new_count = 0
    stored_comments: list[CommunityComment] = []

    async with async_session_factory() as session:
        # Check which URLs already exist to avoid duplicates
        existing_urls_stmt = select(CommunityComment.url).where(
            CommunityComment.url.isnot(None)
        )
        result = await session.execute(existing_urls_stmt)
        existing_urls = {row[0] for row in result.fetchall() if row[0]}

        for c in unique_comments:
            if c["url"] and c["url"] in existing_urls:
                continue

            comment = CommunityComment(
                platform=c["platform"],
                username=c["username"],
                body=c["body"],
                url=c["url"] or None,
                upvotes=c["upvotes"],
                topic_tags=c["topic_tags"],
                published_at=c.get("published_at"),
                fetched_at=datetime.now(tz=timezone.utc),
            )
            session.add(comment)
            stored_comments.append(comment)
            new_count += 1

        await session.commit()

        # Refresh to get auto-generated IDs
        for comment in stored_comments:
            await session.refresh(comment)

    logger.info("Stored %d new community comments in Postgres", new_count)

    # 5. Generate embeddings and store in ChromaDB
    if stored_comments:
        texts = [c.body for c in stored_comments]
        try:
            embeddings = generate_embeddings(texts)
        except Exception as exc:
            logger.error("Community embedding generation failed: %s", exc)
            return new_count

        chroma_ids = [str(c.id) for c in stored_comments]
        chroma_docs = [c.body[:5000] for c in stored_comments]
        chroma_metas = [
            {
                "platform": c.platform,
                "upvotes": c.upvotes,
                "topic_tags": ",".join(c.topic_tags or []),
                "username": c.username,
            }
            for c in stored_comments
        ]

        # Filter out comments with empty embeddings
        valid = [(i, e, d, m) for i, e, d, m in zip(chroma_ids, embeddings, chroma_docs, chroma_metas) if e]
        if valid:
            v_ids, v_embeds, v_docs, v_metas = zip(*valid)
            try:
                community_store = get_community_vector_store()
                community_store.upsert_comments(
                    ids=list(v_ids),
                    embeddings=list(v_embeds),
                    documents=list(v_docs),
                    metadatas=list(v_metas),
                )
            except Exception as exc:
                logger.error("Community ChromaDB upsert failed: %s", exc)

    logger.info("Community pipeline complete: %d new comments", new_count)
    return new_count


if __name__ == "__main__":
    from app.core.logging import setup_logging
    setup_logging()
    result = asyncio.run(run_community_pipeline())
    print(f"Community pipeline complete: {result} new comments")
