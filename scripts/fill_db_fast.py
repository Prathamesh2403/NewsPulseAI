"""
Fast fill script — runs NYT Top Stories + NewsData + Reddit (no comments).

Reddit posts are stored immediately without comment fetching (fetch_comments=False).
Run enrich_comments.py separately after a cooldown period to backfill comments.
"""
import asyncio
import sys
import logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.WARNING)

from collections import Counter


async def main():
    from app.processing.indexer import index_articles
    from app.db.session import async_session_factory
    from app.ingestion.nyt_ingester import NYTIngester
    from app.ingestion.newsdata_ingester import NewsdataIngester
    from app.ingestion.reddit_ingester import RedditRSSIngester
    from app.ingestion.deduplicator import deduplicate_batch
    from sqlalchemy import text

    all_articles = []

    # ── 1. NYT Top Stories (fast — 5 requests, ~150 articles) ─────────────
    print("=== NYT Top Stories ===")
    try:
        nyt = NYTIngester()
        nyt_articles = await nyt.fetch()
        print(f"  NYT: {len(nyt_articles)} articles")
        all_articles.extend(nyt_articles)
    except Exception as e:
        print(f"  NYT failed: {e}")

    # ── 2. NewsData.io (fast — rate-limit is just 1.5s between reqs) ──────
    print("=== NewsData.io ===")
    try:
        nd = NewsdataIngester()
        nd_articles = await nd.fetch()
        print(f"  NewsData: {len(nd_articles)} articles")
        all_articles.extend(nd_articles)
    except Exception as e:
        print(f"  NewsData failed: {e}")

    # ── 3. Reddit RSS — posts only, NO comment fetching ───────────────────
    print("=== Reddit RSS (posts only, comments skipped) ===")
    try:
        reddit = RedditRSSIngester(
            subreddits=["artificial", "MachineLearning", "OpenAI", "technology", "singularity"],
            fetch_comments=False,   # store posts fast; enrich later
        )
        reddit_articles = await reddit.fetch()
        print(f"  Reddit: {len(reddit_articles)} posts")
        all_articles.extend(reddit_articles)
    except Exception as e:
        print(f"  Reddit failed: {e}")

    # ── 4. Dedup + Index ──────────────────────────────────────────────────
    deduped = deduplicate_batch(all_articles)
    print(f"\nTotal after dedup: {len(deduped)} (from {len(all_articles)} raw)")

    if not deduped:
        print("Nothing new to index.")
        return

    print(f"\n=== Indexing {len(deduped)} articles ===")
    count = await index_articles(deduped)
    print(f"Indexed: {count} articles")

    # ── 5. Final DB state ─────────────────────────────────────────────────
    async with async_session_factory() as session:
        r = await session.execute(text(
            "SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY COUNT(*) DESC"
        ))
        rows = r.fetchall()
        total = sum(row[1] for row in rows)
        print(f"\n=== Final DB ({total} total articles) ===")
        for source, cnt in rows:
            print(f"  {source}: {cnt}")

        # Reddit comments coverage
        r2 = await session.execute(text(
            "SELECT source_name, COUNT(*) FROM articles WHERE source='reddit' "
            "GROUP BY source_name ORDER BY source_name"
        ))
        print("\nReddit breakdown by subreddit:")
        for name, cnt in r2.fetchall():
            print(f"  {name}: {cnt}")

        r3 = await session.execute(text(
            "SELECT COUNT(*) FROM articles WHERE source='reddit' "
            "AND comments IS NOT NULL AND jsonb_array_length(comments::jsonb) > 0"
        ))
        print(f"\nReddit posts with comments: {r3.scalar()}")
        print("\nRun 'python enrich_comments.py' to backfill comments for new posts.")


asyncio.run(main())
