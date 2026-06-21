"""
Community matcher.

After ingestion, matches community posts (like Hacker News) to existing news articles.
Matches are primarily by exact URL, then falling back to fuzzy title matching.
When a match is found, the community post's comments are stored as CommunityComment 
rows linked to the matched article.
"""

import logging
from datetime import datetime, timedelta, timezone

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, CommunityComment
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Minimum fuzzy match score to consider a post as related to an article
_MATCH_THRESHOLD = 65


async def match_community_posts() -> int:
    """Match HN and Reddit posts to news articles and store comments.
    
    Returns:
        Number of successful matches made.
    """
    async with async_session_factory() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

        # 1. Get recent community posts (HN, Reddit, DEV.to)
        community_stmt = (
            select(Article)
            .where(Article.source.in_(["hackernews", "reddit", "devto"]))
            .where(Article.fetched_at >= cutoff)
        )
        community_result = await session.execute(community_stmt)
        community_articles = community_result.scalars().all()

        if not community_articles:
            logger.info("No recent community posts to match")
            return 0

        # 2. Get recent non-community news articles
        news_stmt = (
            select(Article)
            .where(Article.source.notin_(["hackernews", "reddit", "devto"]))
            .where(Article.fetched_at >= cutoff)
        )
        news_result = await session.execute(news_stmt)
        news_articles = news_result.scalars().all()

        if not news_articles:
            logger.info("No recent news articles to match against")
            return 0

        logger.info(
            "Matching %d community posts against %d news articles",
            len(community_articles),
            len(news_articles),
        )

        match_count = 0

        for comm_art in community_articles:
            comm_title = comm_art.title.lower().strip()
            
            # Extract the original source ID depending on the platform
            source = comm_art.source
            post_id = ""
            if source == "hackernews":
                post_id = str((comm_art.raw_metadata or {}).get("hn_id", ""))
            elif source == "reddit":
                post_id = str((comm_art.raw_metadata or {}).get("post_id", ""))
            elif source == "devto":
                post_id = str((comm_art.raw_metadata or {}).get("id", ""))

            if not post_id:
                continue

            # Check if we already matched this post (don't double-process)
            existing = await session.execute(
                select(CommunityComment)
                .where(CommunityComment.source == source)
                .where(CommunityComment.source_post_id == post_id)
                .limit(1)
            )
            if existing.scalar_one_or_none():
                continue

            # Find best matching news article
            best_match: Article | None = None
            
            # 1. First try Exact URL match (common for HN)
            if comm_art.url and not comm_art.url.startswith("https://news.ycombinator.com") and not comm_art.url.startswith("https://reddit.com"):
                for news_art in news_articles:
                    # Strip trailing slashes for safer comparison
                    if news_art.url.rstrip("/") == comm_art.url.rstrip("/"):
                        best_match = news_art
                        break

            # 2. Fallback to Fuzzy Title match
            if not best_match:
                best_score = 0
                for news_art in news_articles:
                    score = fuzz.token_sort_ratio(
                        comm_title,
                        news_art.title.lower().strip(),
                    )
                    if score > _MATCH_THRESHOLD and score > best_score:
                        best_match = news_art
                        best_score = score

            if not best_match:
                continue

            logger.info(
                "Matched [%s] post '%s' -> article '%s'",
                source,
                comm_art.title[:50],
                best_match.title[:50],
            )

            # Set the foreign key link on the article if applicable
            if source == "reddit":
                best_match.reddit_post_id = post_id
            elif source == "hackernews":
                best_match.hn_story_id = post_id

            # Extract comments from the community article
            comments_raw = comm_art.comments or []

            if not comments_raw:
                continue

            # We process at most top 10 comments
            comments_to_store = comments_raw[:10]

            for i, c_data in enumerate(comments_to_store):
                # c_data could be a string or a dict. Normalize it.
                if isinstance(c_data, dict):
                    body = c_data.get("body", "")
                    username = c_data.get("username", f"user_{i+1}")
                    upvotes = c_data.get("upvotes", 0)
                else:
                    body = str(c_data)
                    username = f"user_{i+1}"
                    upvotes = 0

                if not body or len(body.strip()) < 5:
                    continue
                
                # Determine permalink
                permalink = ""
                if source == "hackernews":
                    permalink = f"https://news.ycombinator.com/item?id={post_id}"
                elif source == "reddit":
                    permalink = f"https://reddit.com/comments/{post_id}"
                elif source == "devto":
                    permalink = comm_art.url
                
                comment = CommunityComment(
                    article_id=best_match.id,
                    source=source,
                    source_post_id=post_id,
                    username=username,
                    body=body.strip()[:2000],
                    upvotes=upvotes,
                    permalink=permalink,
                    fetched_at=datetime.now(timezone.utc),
                )
                session.add(comment)

            match_count += 1

        await session.commit()
        logger.info("Community matching complete: %d matches found", match_count)
        return match_count
