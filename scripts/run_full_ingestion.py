import asyncio
import logging
from app.core.logging import setup_logging
from app.ingestion.pipeline import run_pipeline
from app.processing.indexer import index_articles

async def main():
    setup_logging()
    logger = logging.getLogger("run_full_ingestion")
    
    logger.info("Starting full ingestion pipeline...")
    new_articles = await run_pipeline()
    
    if new_articles:
        logger.info(f"Indexing {len(new_articles)} new articles...")
        indexed_count = await index_articles(new_articles)
        logger.info(f"Successfully indexed {indexed_count} articles.")
    else:
        logger.info("No new articles to index.")

if __name__ == "__main__":
    asyncio.run(main())
