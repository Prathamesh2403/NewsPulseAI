"""
Live search node for the RAG graph.

Used as a fallback when local vector database retrieval yields weak
or no results. Uses the Tavily API to fetch real-time info.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from tavily import AsyncTavilyClient

from app.core.config import get_settings
from app.core.llm import get_next_tavily_key, mark_tavily_key_bad
from app.rag.state import RAGState

logger = logging.getLogger(__name__)


async def live_search_node(state: RAGState) -> dict[str, Any]:
    """Perform a live web search using Tavily."""
    print("[LIVE SEARCH] Tavily fallback triggered")
    query = state.get("query", "")
    logger.info("Live search node triggered for query: %s", query[:100])

    settings = get_settings()
    if not settings.is_tavily_enabled:
        logger.warning("Live search triggered but Tavily is disabled. Returning empty results.")
        return {"live_search_results": []}

    try:
        # Get key from round-robin pool
        api_key = get_next_tavily_key()
        client = AsyncTavilyClient(api_key=api_key)

        response = await client.search(
            query=query,
            search_depth="advanced",
            max_results=3,
            include_raw_content=False,
            topic="news",
        )

        results = []
        for res in response.get("results", []):
            # Format to look like vector DB articles so generation node can use them easily
            article = {
                "id": f"tavily_{res.get('url', '')}",
                "title": res.get("title", "Live Search Result"),
                "content": res.get("content", ""),
                "url": res.get("url", ""),
                "source": "tavily",
                "source_name": "Web Search (Tavily)",
                "published_at": res.get("published_date", datetime.now(timezone.utc).isoformat()),
                "category": "Live Search",
            }
            results.append(article)

        logger.info("Live search returned %d results", len(results))
        return {"live_search_results": results}

    except Exception as exc:
        s = str(exc).lower()
        if "401" in s or "unauthorized" in s or "credit" in s:
            logger.warning("Tavily key exhausted or invalid: %s", exc)
            mark_tavily_key_bad(api_key)
        else:
            logger.error("Live search failed: %s", exc)
        return {"live_search_results": []}
