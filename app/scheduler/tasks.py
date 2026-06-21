"""
Celery task definitions.

Contains the ``run_ingestion_pipeline`` task that orchestrates
fetching new articles and indexing them into the vector store.
"""

import asyncio
import logging
import time
import datetime

from sqlalchemy.orm import Session

from app.db.session import SyncSessionLocal
from app.db.models import IngestionRun
from app.scheduler.celery_app import celery_app

logger = logging.getLogger(__name__)


async def run_community_pipeline() -> int:
    """Phase 3: Fetch community items."""
    # from app.ingestion.rss_ingester import fetch_rss_feeds
    # optionally: from app.ingestion.hackernews if it exists
    # For now, return 0 as placeholder since specific implementations aren't provided
    return 0


@celery_app.task(
    bind=True,
    name="app.scheduler.tasks.run_community_pipeline",
    max_retries=2,
    default_retry_delay=30,
)
def run_community_pipeline_task(self) -> dict[str, object]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        count = loop.run_until_complete(run_community_pipeline())
        return {"status": "success", "community_items": count}
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.scheduler.tasks.run_ingestion_pipeline",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def run_ingestion_pipeline(self) -> dict[str, object]:
    """Run the full ingestion + processing pipeline.

    1. Fetch articles from all configured news sources.
    2. Index newly fetched articles into ChromaDB.
    3. Run community ingestion pipeline.

    Returns a dict with ``status``, ``new_articles``, and ``community_items`` count.
    Retries up to 3 times with 60-second delay on failure.
    """
    run_id = None
    try:
        from app.ingestion.pipeline import run_pipeline  # type: ignore[import-untyped]
        from app.processing.indexer import index_articles  # type: ignore[import-untyped]

        with SyncSessionLocal() as session:
            run_log = IngestionRun(status="running")
            session.add(run_log)
            session.commit()
            run_id = run_log.id

        start = time.time()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Phase 1: News
            logger.info("Ingestion pipeline starting ...")
            new_articles = loop.run_until_complete(run_pipeline())
            
            # Phase 2: Index
            count = 0
            if new_articles:
                count = loop.run_until_complete(index_articles(new_articles))
                logger.info("Ingestion complete — indexed %d new articles", count)
            else:
                logger.info("Ingestion complete — no new articles found")
                
            # Phase 3: Community ingestion
            community_count = loop.run_until_complete(run_community_pipeline())

            elapsed = round(time.time() - start, 2)
            
            with SyncSessionLocal() as session:
                run_log = session.get(IngestionRun, run_id)
                if run_log:
                    run_log.status = "success"
                    run_log.new_articles = count
                    run_log.community_items = community_count
                    run_log.duration_seconds = elapsed
                    run_log.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    session.commit()

            return {
                "status": "success",
                "new_articles": count,
                "community_items": community_count,
                "duration_seconds": elapsed
            }
        finally:
            loop.close()
    except Exception as exc:
        logger.exception("Ingestion pipeline failed, retrying ...")
        if run_id:
            try:
                with SyncSessionLocal() as session:
                    run_log = session.get(IngestionRun, run_id)
                    if run_log:
                        run_log.status = "failed"
                        run_log.error_message = str(exc)
                        run_log.completed_at = datetime.datetime.now(datetime.timezone.utc)
                        session.commit()
            except Exception:
                pass
        raise self.retry(exc=exc)

# ============================================================
# HOW TO TEST CELERY LOCALLY (WINDOWS)
# Run each of these in a separate PowerShell/terminal window
# in this exact order:
#
# Terminal 1 (Docker — Redis):
#   docker run -p 6379:6379 redis
#
# Terminal 2 (FastAPI backend):
#   uvicorn app.main:app --reload
#
# Terminal 3 (Celery Worker — must use --pool=solo on Windows):
#   celery -A app.scheduler.celery_app worker 
#          --loglevel=info --pool=solo -Q news_bot
#
# Terminal 4 (Celery Beat — triggers tasks on schedule):
#   celery -A app.scheduler.celery_app beat --loglevel=info
#
# VERIFY IT WORKS:
#   Option A (immediate): POST http://localhost:8000/api/v1/admin/ingestion/trigger
#   Option B (scheduled): wait 2 minutes, then check:
#                         GET http://localhost:8000/api/v1/admin/ingestion/status
#
# WATCH THE LOGS:
#   Terminal 3 (Worker) should show:
#     [INFO] Received task: app.scheduler.tasks.run_ingestion_pipeline
#     [INFO] Ingestion pipeline starting...
#     [INFO] Ingestion complete — indexed N new articles
#   Terminal 4 (Beat) should show every 2 minutes:
#     [INFO] Scheduler: Sending due task run-ingestion-pipeline
# ============================================================
