"""
News ingestion pipeline orchestrator.

Runs all enabled NEWS ingesters concurrently (Newsdata, NewsAPI, ApiTube),
normalizes and deduplicates results, persists a raw JSON snapshot,
and returns new unique articles for downstream processing.

Community discussions (HN, Reddit, DevTo) are handled by community_pipeline.py.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update

from app.core.config import get_settings
from app.db.models import IngestionRun
from app.db.session import async_session_factory
from app.ingestion.deduplicator import deduplicate_batch, filter_existing_urls
from app.ingestion.newsdata_ingester import NewsdataIngester
from app.ingestion.newsapi_ingester import NewsAPIIngester
from app.ingestion.apitube_ingester import ApiTubeIngester
from app.schemas.article import RawArticle

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path("data/raw")


def _get_enabled_ingesters() -> list:
    """Instantiate all NEWS ingesters whose API keys are configured."""
    ingesters = []
    candidates = [
        NewsdataIngester(),
        NewsAPIIngester(),
        ApiTubeIngester(),
    ]
    for ing in candidates:
        if ing.is_enabled:
            ingesters.append(ing)
            logger.info("Enabled ingester: %s", ing.source_name)
        else:
            logger.info("Skipped ingester (disabled): %s", ing.source_name)
    return ingesters


def _save_raw_snapshot(articles: list[RawArticle]) -> str:
    """Save raw articles as a JSON snapshot for debugging/audit."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = RAW_DATA_DIR / f"{timestamp}.json"
    data = [a.model_dump(mode="json") for a in articles]
    filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("Saved raw snapshot: %s (%d articles)", filepath, len(data))
    return str(filepath)


async def run_pipeline() -> list[RawArticle]:
    """Execute the full news ingestion pipeline.

    Steps:
        1. Create IngestionRun record in DB
        2. Instantiate and run all enabled ingesters concurrently
        3. Apply quality filters (>250 words, has image)
        4. Deduplicate within the batch (URL + fuzzy title)
        5. Filter against existing DB records (by URL)
        6. Save raw JSON snapshot
        7. Update IngestionRun record with results
        8. Return list of new unique articles

    Returns:
        List of new, deduplicated RawArticle objects ready for processing.
    """
    settings = get_settings()
    ingesters = _get_enabled_ingesters()

    if not ingesters:
        logger.warning("No ingesters are enabled. Check your API keys in .env")
        return []

    # 1. Create IngestionRun record
    run = IngestionRun(
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    async with async_session_factory() as session:
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    logger.info("Ingestion run %s started", run_id)

    # 2. Run all ingesters concurrently
    all_articles: list[RawArticle] = []
    source_breakdown: dict[str, int] = {}
    errors: list[str] = []

    tasks = [ing.fetch() for ing in ingesters]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for ing, result in zip(ingesters, results):
        if isinstance(result, Exception):
            error_msg = f"{ing.source_name}: {result}"
            errors.append(error_msg)
            logger.error("Ingester %s failed: %s", ing.source_name, result)
            source_breakdown[ing.source_name] = 0
        else:
            all_articles.extend(result)
            source_breakdown[ing.source_name] = len(result)
            logger.info(
                "Ingester %s returned %d articles",
                ing.source_name,
                len(result),
            )

    logger.info("Total raw articles from all sources: %d", len(all_articles))

    # 3. Apply quality filters: >= 250 words AND has image URL
    valid_articles = [
        a for a in all_articles
        if len(a.content.split()) >= 250 and a.image_url
    ]
    logger.info("Articles after quality filter (250w + image): %d", len(valid_articles))
    all_articles = valid_articles

    # 4. Deduplicate within batch
    deduped = deduplicate_batch(all_articles)

    # 5. Filter against existing DB records
    async with async_session_factory() as session:
        new_articles = await filter_existing_urls(deduped, session)

    # 6. Save raw snapshot
    if all_articles:
        _save_raw_snapshot(all_articles)

    # 7. Update IngestionRun record
    async with async_session_factory() as session:
        await session.execute(
            update(IngestionRun)
            .where(IngestionRun.id == run_id)
            .values(
                completed_at=datetime.now(timezone.utc),
                status="completed" if not errors else "completed_with_errors",
                sources_breakdown=source_breakdown,
                new_articles=len(new_articles),
                error_message="\n".join(errors) if errors else None,
            )
        )
        await session.commit()

    logger.info(
        "Ingestion run %s completed: %d new articles (sources: %s)",
        run_id,
        len(new_articles),
        source_breakdown,
    )

    return new_articles


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging()
    result = asyncio.run(run_pipeline())
    print(f"Pipeline complete: {len(result)} new articles")
