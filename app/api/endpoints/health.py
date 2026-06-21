"""
Health check endpoint.

Reports connectivity status for PostgreSQL and ChromaDB, plus
high-level statistics like total article count and last ingestion time.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, IngestionRun
from app.db.session import get_db
from app.db.vector_store import get_vector_store
from app.schemas.trends import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Return system health status including database and vector store connectivity."""
    response = HealthResponse()

    # --- Check PostgreSQL connectivity ---
    try:
        await db.execute(text("SELECT 1"))
        response.database = "connected"
    except Exception as exc:
        logger.error("PostgreSQL health check failed: %s", exc)
        response.database = "disconnected"
        response.status = "degraded"

    # --- Check ChromaDB status ---
    try:
        vs = get_vector_store()
        stats = vs.get_stats()
        response.vector_store = "connected"
        response.vector_store_count = stats.get("total_documents", 0)
    except Exception as exc:
        logger.error("ChromaDB health check failed: %s", exc)
        response.vector_store = "disconnected"
        response.status = "degraded"

    # --- Total article count ---
    try:
        result = await db.execute(select(func.count(Article.id)))
        response.total_articles = result.scalar_one_or_none() or 0
    except Exception as exc:
        logger.error("Article count query failed: %s", exc)

    # --- Last ingestion run timestamp ---
    try:
        result = await db.execute(
            select(IngestionRun.completed_at)
            .where(IngestionRun.status == "completed")
            .order_by(IngestionRun.completed_at.desc())
            .limit(1)
        )
        last_run = result.scalar_one_or_none()
        if last_run is not None:
            response.last_ingestion = last_run
    except Exception as exc:
        logger.error("Ingestion run query failed: %s", exc)

    # If both services are down, mark overall status as unhealthy
    if response.database == "disconnected" and response.vector_store == "disconnected":
        response.status = "unhealthy"

    return response
