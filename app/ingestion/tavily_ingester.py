"""
Tavily Search API ingester.

Uses the ``tavily-python`` SDK to search for recent AI / tech news
articles via Tavily's advanced search mode.  Disabled by default —
only runs when ``TAVILY_API_KEY`` is set.
"""

from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import normalize_tavily_result
from app.schemas.article import RawArticle

logger = get_logger(__name__)

_DEFAULT_QUERIES: list[str] = [
    "artificial intelligence news",
    "machine learning breakthroughs",
    "AI technology startups",
]


class TavilyIngester(BaseIngester):
    """Fetches articles using the Tavily search API."""

    def __init__(
        self,
        queries: list[str] | None = None,
        max_results: int = 10,
    ) -> None:
        """Initialise the Tavily ingester.

        Args:
            queries: Search terms to run. Defaults to ``_DEFAULT_QUERIES``.
            max_results: Maximum results per query (Tavily cap).
        """
        self._settings = get_settings()
        self._queries = queries or _DEFAULT_QUERIES
        self._max_results = max_results

    # -- BaseIngester interface -----------------------------------------------

    @property
    def source_name(self) -> str:  # noqa: D401
        """Source identifier."""
        return "tavily"

    @property
    def is_enabled(self) -> bool:
        """Whether the Tavily API key is configured."""
        return self._settings.is_tavily_enabled

    async def fetch(self) -> list[RawArticle]:
        """Run all Tavily searches and return normalised articles.

        The Tavily SDK is synchronous, but the overhead is minimal
        (single HTTP POST each), so we call it directly inside the
        async function.  For true non-blocking behaviour, wrap with
        ``asyncio.to_thread`` if necessary.

        Returns:
            List of ``RawArticle`` objects.
        """
        if not self._settings.is_tavily_enabled:
            logger.info("Tavily ingester skipped — no API key configured.")
            return []

        try:
            from tavily import TavilyClient  # noqa: WPS433 – conditional import
        except ImportError:
            logger.error(
                "tavily-python package is not installed. "
                "Install with: pip install tavily-python"
            )
            return []

        articles: list[RawArticle] = []

        try:
            client = TavilyClient(api_key=self._settings.tavily_api_key)
        except Exception:
            logger.exception("Failed to initialise TavilyClient.")
            return []

        for query in self._queries:
            try:
                response: dict[str, Any] = client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=self._max_results,
                    topic="news",
                    include_raw_content=False,
                )

                results: list[dict[str, Any]] = response.get("results") or []
                for result in results:
                    try:
                        article = normalize_tavily_result(result)
                        articles.append(article)
                    except Exception:
                        logger.exception(
                            "Failed to normalize Tavily result for query='%s'.",
                            query,
                        )

                logger.debug(
                    "Tavily query='%s' returned %d results.",
                    query,
                    len(results),
                )

            except Exception:
                logger.exception(
                    "Tavily search failed for query='%s'.",
                    query,
                )

        logger.info(
            "Tavily ingestion complete — fetched %d articles across %d queries.",
            len(articles),
            len(self._queries),
        )
        return articles
