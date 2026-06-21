"""Full pipeline fill script — ingest from all sources and index."""
import asyncio
import sys
import logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.WARNING)

from collections import Counter


async def main():
    from app.ingestion.pipeline import run_pipeline
    from app.processing.indexer import index_articles
    from app.db.session import async_session_factory
    from sqlalchemy import text

    print("=== Phase 1: Full Ingestion (NYT + NewsData + GNews + Reddit) ===")
    articles = await run_pipeline()

    by_source = Counter(a.source for a in articles)
    print(f"\nTotal new articles ingested: {len(articles)}")
    for src, cnt in sorted(by_source.items()):
        print(f"  {src}: {cnt}")

    reddit = [a for a in articles if a.source == "reddit"]
    with_comments = [a for a in reddit if len(a.comments) > 0]
    total_comments = sum(len(a.comments) for a in reddit)
    if reddit:
        print(f"  Reddit with comments: {len(with_comments)}/{len(reddit)} | Total comments: {total_comments}")

    if not articles:
        print("No new articles — check source logs above")
        return

    print(f"\n=== Phase 2: Indexing {len(articles)} articles ===")
    count = await index_articles(articles)
    print(f"Indexed: {count} articles")

    # Final DB counts
    async with async_session_factory() as session:
        r = await session.execute(text("SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY COUNT(*) DESC"))
        rows = r.fetchall()
        total = sum(row[1] for row in rows)
        print(f"\n=== Final DB State ({total} total articles) ===")
        for source, cnt in rows:
            print(f"  {source}: {cnt}")

        r2 = await session.execute(text(
            "SELECT COUNT(*) FROM articles WHERE comments IS NOT NULL AND jsonb_array_length(comments::jsonb) > 0"
        ))
        articles_with_comments = r2.scalar()
        print(f"  Articles with stored comments: {articles_with_comments}")


asyncio.run(main())
