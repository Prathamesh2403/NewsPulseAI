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


@router.post("/ingestion/sync-chroma")
async def sync_chromadb(background_tasks: BackgroundTasks):
    """Backfill ChromaDB with all articles currently in PostgreSQL.

    Because Render Free Tier wipes local disks on every deploy, the ChromaDB
    instance starts empty. This endpoint fetches all articles from the
    database, generates their embeddings via the Gemini API, and inserts
    them into ChromaDB so the AI chat can find them.
    """
    background_tasks.add_task(run_sync_chromadb_directly)
    return {
        "status": "triggered",
        "message": "ChromaDB sync started as a background task. Check Render logs.",
    }


async def run_sync_chromadb_directly() -> None:
    """Background task to sync Postgres articles to ChromaDB.

    Uses the async session (asyncpg → Supabase) so it works on Render
    where no local Postgres exists.
    """
    from app.db.models import Article
    from app.processing.embedder import generate_embeddings, prepare_embedding_text
    from app.db.vector_store import get_vector_store
    from app.db.session import async_session_factory
    from sqlalchemy import select as sa_select

    start = time.time()
    logger.info("[CHROMA SYNC] Starting ChromaDB backfill from Postgres")

    try:
        # 1. Fetch all articles from PostgreSQL via async session (→ Supabase)
        async with async_session_factory() as session:
            result = await session.execute(sa_select(Article))
            articles = result.scalars().all()

        if not articles:
            logger.info("[CHROMA SYNC] No articles found in Postgres.")
            return

        logger.info("[CHROMA SYNC] Found %d articles. Generating embeddings...", len(articles))

        # 2. Prepare texts for embedding
        embedding_texts = [
            prepare_embedding_text(a.title, a.summary, a.content)
            for a in articles
        ]

        # 3. Generate embeddings (Gemini API)
        embeddings = generate_embeddings(embedding_texts)

        # 4. Prepare ChromaDB records
        chroma_ids = []
        chroma_embeddings = []
        chroma_documents = []
        chroma_metadatas = []

        for i, article in enumerate(articles):
            # Skip if embedding generation failed for this article
            if not embeddings[i]:
                continue

            chroma_ids.append(article.embedding_id)
            chroma_embeddings.append(embeddings[i])
            chroma_documents.append(embedding_texts[i][:5000])
            chroma_metadatas.append(
                {
                    "category": article.category or "Other",
                    "source": article.source or "",
                    "source_name": article.source_name or "",
                    "published_at": (
                        article.published_at.isoformat()
                        if article.published_at
                        else ""
                    ),
                    "sentiment_label": article.sentiment_label or "neutral",
                    "sentiment_score": article.sentiment_score or 0.0,
                    "title": article.title[:500] if article.title else "",
                    "url": article.url or "",
                }
            )

        # 5. Upsert to ChromaDB
        if chroma_ids:
            vector_store = get_vector_store()
            vector_store.upsert_articles(
                ids=chroma_ids,
                embeddings=chroma_embeddings,
                documents=chroma_documents,
                metadatas=chroma_metadatas,
            )

        elapsed = round(time.time() - start, 2)
        logger.info(
            "[CHROMA SYNC] Complete — %d articles synced to ChromaDB in %ss",
            len(chroma_ids),
            elapsed,
        )
    except Exception as exc:
        logger.error("[CHROMA SYNC] Failed: %s", exc, exc_info=True)
