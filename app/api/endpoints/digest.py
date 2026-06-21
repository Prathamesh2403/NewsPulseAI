"""
Daily digest endpoint.

Returns the latest articles optionally filtered by category and/or date,
formatted as a digest of article summaries.
"""

import logging
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article
from app.db.session import get_db
from app.schemas.trends import DigestItem, DigestResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/digest", response_model=DigestResponse)
async def get_digest(
    category: str | None = Query(default=None, description="Filter by article category"),
    date: str | None = Query(
        default=None,
        description="Filter by date in ISO format (YYYY-MM-DD)",
        alias="date",
    ),
    db: AsyncSession = Depends(get_db),
) -> DigestResponse:
    """Return the top 20 latest article summaries, optionally filtered."""
    stmt = select(Article).order_by(Article.published_at.desc()).limit(20)

    # --- Apply category filter ---
    if category:
        stmt = stmt.where(Article.category.ilike(category))

    # --- Apply date filter ---
    parsed_date: date | None = None
    if date:
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format '{date}'. Expected YYYY-MM-DD.",
            )
        day_start = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(parsed_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Article.published_at.between(day_start, day_end))

    result = await db.execute(stmt)
    articles = result.scalars().all()

    digest_items: list[DigestItem] = [
        DigestItem(
            title=article.title,
            summary=article.summary or article.content[:300],
            url=article.url,
            source=article.source,
            source_name=article.source_name or "",
            category=article.category,
            published_at=article.published_at,
        )
        for article in articles
    ]

    return DigestResponse(
        digest=digest_items,
        category=category,
        date=date,
    )
