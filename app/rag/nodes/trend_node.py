"""
Trend analysis node for the RAG graph.

Queries PostgreSQL directly for aggregate statistics (article counts
by category, sentiment distribution) and optionally sends the stats
to Gemini for natural-language interpretation.
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.exceptions import RAGError
from app.db.models import Article
from app.db.session import async_session_factory
from app.rag.prompts.trend_prompt import TREND_SYSTEM_PROMPT, TREND_USER_TEMPLATE
from app.rag.state import RAGState

logger = logging.getLogger(__name__)


def _build_date_filters(
    filters: dict[str, Any],
) -> list[Any]:
    """Build SQLAlchemy date filter clauses from state filters.

    Args:
        filters: Sanitized filter dict from the router node.

    Returns:
        List of SQLAlchemy filter expressions.
    """
    clauses: list[Any] = []

    date_from = filters.get("date_from")
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            clauses.append(Article.published_at >= dt_from)
        except (ValueError, TypeError):
            logger.warning("Invalid date_from filter: %s", date_from)

    date_to = filters.get("date_to")
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            clauses.append(Article.published_at <= dt_to)
        except (ValueError, TypeError):
            logger.warning("Invalid date_to filter: %s", date_to)

    category = filters.get("category")
    if category:
        clauses.append(Article.category == category)

    source = filters.get("source")
    if source:
        clauses.append(Article.source == source)

    return clauses


async def _fetch_aggregate_stats(
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Query PostgreSQL for aggregate article statistics.

    Runs three queries inside a single session:
    1. Article counts grouped by category
    2. Article counts grouped by sentiment label
    3. Total article count

    Args:
        filters: Sanitized metadata filters.

    Returns:
        Dict with 'categories', 'sentiment', and 'total_articles'.
    """
    date_clauses = _build_date_filters(filters)

    async with async_session_factory() as session:
        # --- Category counts ---
        category_stmt = (
            select(Article.category, func.count(Article.id))
            .where(*date_clauses)
            .group_by(Article.category)
            .order_by(func.count(Article.id).desc())
        )
        category_result = await session.execute(category_stmt)
        category_rows = category_result.all()

        categories: list[dict[str, Any]] = [
            {"category": row[0] or "Uncategorized", "count": row[1]}
            for row in category_rows
        ]

        # --- Sentiment distribution ---
        sentiment_stmt = (
            select(Article.sentiment_label, func.count(Article.id))
            .where(*date_clauses)
            .group_by(Article.sentiment_label)
            .order_by(func.count(Article.id).desc())
        )
        sentiment_result = await session.execute(sentiment_stmt)
        sentiment_rows = sentiment_result.all()

        sentiment: dict[str, int] = {}
        for row in sentiment_rows:
            label = row[0] or "unknown"
            sentiment[label] = row[1]

        # --- Total count ---
        total_stmt = select(func.count(Article.id)).where(*date_clauses)
        total_result = await session.execute(total_stmt)
        total_articles: int = total_result.scalar_one_or_none() or 0

    return {
        "categories": categories,
        "sentiment": sentiment,
        "total_articles": total_articles,
    }


def _format_stats_for_llm(stats: dict[str, Any]) -> str:
    """Format aggregate stats into a human-readable string for the LLM.

    Args:
        stats: The raw stats dict from ``_fetch_aggregate_stats``.

    Returns:
        Multi-line formatted string.
    """
    lines: list[str] = []

    lines.append(f"Total articles: {stats['total_articles']}")
    lines.append("")

    lines.append("Articles by category:")
    for cat in stats.get("categories", []):
        lines.append(f"  - {cat['category']}: {cat['count']}")
    lines.append("")

    lines.append("Sentiment distribution:")
    for label, count in stats.get("sentiment", {}).items():
        lines.append(f"  - {label}: {count}")

    return "\n".join(lines)


async def trend_node(state: RAGState) -> dict[str, Any]:
    """Compute aggregate trend statistics and generate interpretation.

    Queries PostgreSQL for category and sentiment distributions,
    then optionally sends the stats to Gemini for a concise
    natural-language summary.

    Args:
        state: Current RAG graph state.

    Returns:
        Partial state update with 'response' and empty 'citations'.
    """
    filters = state.get("filters", {})

    logger.info("Trend node: computing aggregates with filters=%s", filters)

    try:
        stats = await _fetch_aggregate_stats(filters)

        if stats["total_articles"] == 0:
            return {
                "response": (
                    "No articles found in the database for the specified "
                    "filters. Try broadening the timeframe or removing filters."
                ),
                "citations": [],
            }

        stats_text = _format_stats_for_llm(stats)
        logger.debug("Trend stats:\n%s", stats_text)

        # Try to get LLM interpretation
        settings = get_settings()
        if settings.is_llm_enabled:
            from langchain_core.messages import HumanMessage, SystemMessage
            from app.core.llm import invoke_gemini_with_fallback

            messages = [
                SystemMessage(content=TREND_SYSTEM_PROMPT),
                HumanMessage(
                    content=TREND_USER_TEMPLATE.format(stats=stats_text)
                ),
            ]

            response = await invoke_gemini_with_fallback(messages, temperature=0.5)
            interpretation = (
                response.content if hasattr(response, "content") else str(response)
            )

            full_response = (
                f"**Trend Analysis**\n\n"
                f"{stats_text}\n\n"
                f"**Interpretation:**\n{interpretation}"
            )
        else:
            # No LLM available — return raw stats
            full_response = f"**Trend Statistics**\n\n{stats_text}"

        logger.info("Trend node complete")
        return {"response": full_response, "citations": []}

    except Exception as exc:
        logger.warning("Trend node error, returning raw stats: %s", exc)
        # Return basic stats without LLM interpretation
        try:
            stats = await _fetch_aggregate_stats(filters)
            stats_text = _format_stats_for_llm(stats)
            return {
                "response": f"**Trend Statistics**\n\n{stats_text}",
                "citations": [],
            }
        except Exception:
            return {
                "response": "Unable to compute trend statistics at this time.",
                "citations": [],
            }
