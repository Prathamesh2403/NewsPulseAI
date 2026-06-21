"""
Articles API — paginated listing, featured articles, and detail endpoints.
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article
from app.db.session import get_db
from app.schemas.article import (
    ArticleListResponse,
    ArticleResponse,
    ArticleSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/articles", response_model=ArticleListResponse)
async def list_articles(
    category: str | None = Query(default=None, description="Filter by article category"),
    source: str | None = Query(default=None, description="Filter by source key (e.g. newsapi, apitube, newsdata)"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """Return a paginated list of articles with optional filters."""
    filters: list = []

    if category and category.lower() != "all":
        filters.append(Article.category.ilike(category))

    if source:
        filters.append(Article.source.ilike(source))

    # --- Total count ---
    count_stmt = select(func.count(Article.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one_or_none() or 0

    total_pages = max(1, math.ceil(total / limit))

    # --- Fetch page ---
    offset = (page - 1) * limit
    items_stmt = (
        select(Article)
        .order_by(Article.published_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
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
        page_size=limit,
        total_pages=total_pages,
    )


@router.get("/articles/featured", response_model=list[ArticleSummaryResponse])
async def get_featured_articles(
    db: AsyncSession = Depends(get_db),
) -> list[ArticleSummaryResponse]:
    """Return top 5 articles for 'Today's Pick' sidebar.
    
    Priority: featured articles first, then most recent from last 24h.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    stmt = (
        select(Article)
        .where(Article.published_at >= cutoff)
        .order_by(
            Article.is_featured.desc(),
            Article.published_at.desc().nullslast(),
        )
        .limit(5)
    )

    result = await db.execute(stmt)
    articles = result.scalars().all()

    # If fewer than 5 from last 24h, backfill with most recent overall
    if len(articles) < 5:
        existing_ids = {a.id for a in articles}
        backfill_stmt = (
            select(Article)
            .where(Article.id.notin_(existing_ids))
            .order_by(Article.published_at.desc().nullslast())
            .limit(5 - len(articles))
        )
        backfill_result = await db.execute(backfill_stmt)
        articles.extend(backfill_result.scalars().all())

    return [
        ArticleSummaryResponse(
            id=str(a.id),
            title=a.title,
            summary=a.summary,
            url=a.url,
            source=a.source,
            source_name=a.source_name or "",
            category=a.category,
            sentiment_label=a.sentiment_label,
            published_at=a.published_at,
            image_url=a.image_url,
        )
        for a in articles
    ]


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article_detail(
    article_id: str,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Return full article detail."""
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content=article.content,
        summary=article.summary,
        url=article.url,
        source=article.source,
        source_name=article.source_name or "",
        category=article.category,
        sentiment_label=article.sentiment_label,
        sentiment_score=article.sentiment_score,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        image_url=article.image_url,
        image_url_original=article.image_url_original,
    )
