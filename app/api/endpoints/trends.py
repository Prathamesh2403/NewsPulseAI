"""
Trends endpoint.

Aggregates category counts and sentiment breakdowns from the articles
table for a configurable timeframe.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article
from app.db.session import get_db
from app.schemas.trends import (
    CategoryCount,
    SentimentBreakdown,
    TrendData,
    TrendsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Map timeframe shorthand to number of days
_TIMEFRAME_MAP: dict[str, int] = {
    "24h": 1,
    "7d": 7,
    "30d": 30,
}


def _parse_timeframe(raw: str) -> tuple[int, str]:
    """Convert a timeframe string to (number of days, human-readable label).

    Raises:
        HTTPException: If the timeframe value is not recognised.
    """
    days = _TIMEFRAME_MAP.get(raw)
    if days is None:
        allowed = ", ".join(sorted(_TIMEFRAME_MAP.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe '{raw}'. Allowed values: {allowed}",
        )
    label = f"last {days} day{'s' if days != 1 else ''}"
    return days, label


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    category: str | None = Query(default=None, description="Filter by article category"),
    timeframe: str = Query(default="7d", description="Timeframe: 24h, 7d, or 30d"),
    db: AsyncSession = Depends(get_db),
) -> TrendsResponse:
    """Return aggregated trend statistics for the given timeframe."""
    days, timeframe_label = _parse_timeframe(timeframe)
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # --- Base filter ---
    base_filter = [Article.published_at >= since]
    if category:
        base_filter.append(Article.category.ilike(category))

    # --- Category counts ---
    cat_stmt = (
        select(
            Article.category,
            func.count(Article.id).label("cnt"),
        )
        .where(*base_filter)
        .where(Article.category.isnot(None))
        .group_by(Article.category)
        .order_by(func.count(Article.id).desc())
    )
    cat_result = await db.execute(cat_stmt)
    category_counts = [
        CategoryCount(category=row.category, count=row.cnt)
        for row in cat_result.all()
    ]

    # --- Sentiment breakdown ---
    sent_stmt = select(
        func.count(
            case((Article.sentiment_label == "positive", Article.id))
        ).label("positive"),
        func.count(
            case((Article.sentiment_label == "neutral", Article.id))
        ).label("neutral"),
        func.count(
            case((Article.sentiment_label == "negative", Article.id))
        ).label("negative"),
    ).where(*base_filter)
    sent_result = await db.execute(sent_stmt)
    sent_row = sent_result.one()
    sentiment = SentimentBreakdown(
        positive=sent_row.positive,
        neutral=sent_row.neutral,
        negative=sent_row.negative,
    )

    # --- Total article count in window ---
    total_stmt = select(func.count(Article.id)).where(*base_filter)
    total_result = await db.execute(total_stmt)
    total_articles = total_result.scalar_one_or_none() or 0

    trend_data = TrendData(
        categories=category_counts,
        sentiment=sentiment,
        total_articles=total_articles,
        timeframe=timeframe_label,
    )
    return TrendsResponse(data=trend_data)
