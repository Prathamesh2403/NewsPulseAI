"""
FastAPI application factory.

Creates the ``app`` instance used by Uvicorn, wiring up middleware,
routers, and lifecycle hooks.
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


def _prewarm_embedder() -> None:
    """Load the SentenceTransformer model into memory at startup.

    Eliminates the ~20-second cold-start delay on the first chat query.
    The embedder module uses a module-level singleton, so one call here
    is enough to trigger the full model load.
    """
    try:
        from app.processing.embedder import generate_embeddings
        generate_embeddings(["warmup"])
        logger.info("Embedding model pre-warmed successfully.")
    except Exception as exc:
        logger.warning("Could not pre-warm embedder: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Startup: configure logging, pre-warm the embedding model so the first
             chat query doesn't incur a ~20-second cold-start delay.
    Shutdown: release resources if needed.
    """
    setup_logging()
    logger.info("AI/Tech News Intelligence Assistant starting up ...")
    
    settings = get_settings()
    if not settings.is_tavily_enabled:
        print("WARNING: TAVILY_API_KEY not set — live search fallback disabled")

    # Pre-warm the embedding model in a thread (it's CPU-bound)
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _prewarm_embedder)
    except Exception as exc:
        logger.warning("Embedding model pre-warm failed (non-fatal): %s", exc)

    if settings.environment == "production":
        logger.info("Production mode — Celery/Redis skipped")
    else:
        try:
            from app.scheduler.celery_app import celery_app
            celery_app.control.ping(timeout=1)
            logger.info("Redis broker: connected")
            logger.info("Current beat schedule: %s", celery_app.conf.beat_schedule)
        except Exception:
            logger.warning("Redis broker: NOT reachable — scheduler disabled")

    yield
    logger.info("Application shutting down ...")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI/Tech News Intelligence Assistant",
        description="Agentic RAG chatbot for AI/tech news",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware — include Vercel frontend URL from env
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            settings.frontend_url,        # Vercel URL in production
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all API routes
    app.include_router(api_router)

    # Root health check (used by Render / Railway healthcheckPath)
    @app.get("/", tags=["health"])
    def root():
        return {
            "status": "ok",
            "service": "NewsPulse AI API",
            "environment": settings.environment,
        }

    return app


# Module-level instance for ``uvicorn app.main:app``
app = create_app()
