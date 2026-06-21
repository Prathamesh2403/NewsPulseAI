"""
Sources endpoint — paginated article listing.

Supports filtering by category, source name, and date range.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article
from app.db.session import get_db
from app.schemas.article import ArticleListResponse, ArticleSummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sources", response_model=ArticleListResponse)
async def list_articles(
    category: str | None = Query(default=None, description="Filter by article category"),
    source: str | None = Query(default=None, description="Filter by source key (e.g. nyt, reddit)"),
    date_from: str | None = Query(
        default=None,
        description="Start date filter (ISO YYYY-MM-DD)",
    ),
    date_to: str | None = Query(
        default=None,
        description="End date filter (ISO YYYY-MM-DD)",
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """Return a paginated list of articles with optional filters."""
    filters: list = []

    if category:
        filters.append(Article.category.ilike(category))

    if source:
        filters.append(Article.source.ilike(source))

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date_from format '{date_from}'. Expected YYYY-MM-DD.",
            )
        filters.append(Article.published_at >= dt_from)

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc,
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date_to format '{date_to}'. Expected YYYY-MM-DD.",
            )
        filters.append(Article.published_at <= dt_to)

    # --- Total count ---
    count_stmt = select(func.count(Article.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one_or_none() or 0

    total_pages = max(1, math.ceil(total / page_size))

    # --- Fetch page ---
    offset = (page - 1) * page_size
    items_stmt = (
        select(Article)
        .order_by(Article.published_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    if filters:
        items_stmt = items_stmt.where(*filters)

    items_result = await db.execute(items_stmt)
    articles = items_result.scalars().all()

    article_responses = [
        ArticleSummaryResponse(
            id=str(article.id),
            title=article.title,
            summary=article.summary,
            url=article.url,
            source=article.source,
            source_name=article.source_name or "",
            category=article.category,
            sentiment_label=article.sentiment_label,
            published_at=article.published_at,
            image_url=article.image_url,
        )
        for article in articles
    ]

    return ArticleListResponse(
        articles=article_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
