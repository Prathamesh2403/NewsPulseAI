import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.session import SyncSessionLocal
from app.db.models import IngestionRun

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/ingestion/status")
async def get_ingestion_status():
    """Returns the last 5 IngestionRun rows ordered by started_at DESC."""
    with SyncSessionLocal() as session:
        stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(5)
        runs = session.scalars(stmt).all()
        return [
            {
                "id": run.id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "status": run.status,
                "new_articles": run.new_articles,
                "community_items": run.community_items,
                "duration_seconds": run.duration_seconds,
            }
            for run in runs
        ]


@router.post("/ingestion/trigger")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Manually triggers the ingestion pipeline.

    In production (Render): runs directly as a FastAPI BackgroundTask —
    no Celery or Redis needed.
    In development (Docker): dispatches to the Celery worker via Redis.
    """
    if settings.environment == "production":
        # Production: run directly as FastAPI background task
        background_tasks.add_task(run_ingestion_directly)
        return {
            "status": "triggered",
            "mode": "background_task",
            "message": "Ingestion started as background task",
        }
    else:
        # Development: use Celery as before
        from app.scheduler.tasks import run_ingestion_pipeline
        task = run_ingestion_pipeline.delay()
        return {
            "status": "triggered",
            "mode": "celery",
            "task_id": task.id,
        }


async def run_ingestion_directly() -> None:
    """Run the full ingestion + indexing pipeline directly inside the
    FastAPI process.

    Used in production (Render) where the Celery worker is not running.
    The function is intentionally fire-and-forget — errors are logged
    but not re-raised so the background task doesn't crash the server.
    """
    from app.ingestion.pipeline import run_pipeline
    from app.processing.indexer import index_articles

    start = time.time()
    logger.info("[PRODUCTION INGESTION] Starting direct pipeline run")

    try:
        # Phase 1: ingest new articles from all enabled sources
        new_articles = await run_pipeline()

        # Phase 2: embed and index into ChromaDB
        count = 0
        if new_articles:
            count = await index_articles(new_articles)

        elapsed = round(time.time() - start, 2)
        logger.info(
            "[PRODUCTION INGESTION] Complete — %d new articles indexed in %ss",
            count,
            elapsed,
        )
    except Exception as exc:
        logger.error("[PRODUCTION INGESTION] Failed: %s", exc, exc_info=True)
