"""
Main API router.

Aggregates all endpoint routers under the ``/api/v1/`` prefix.
"""

from fastapi import APIRouter

from app.api.endpoints import articles, chat, digest, health, sources, trends, article_chat, admin

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(article_chat.router, tags=["article_chat"])
api_router.include_router(digest.router, tags=["digest"])
api_router.include_router(trends.router, tags=["trends"])
api_router.include_router(sources.router, tags=["sources"])
api_router.include_router(articles.router, tags=["articles"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
