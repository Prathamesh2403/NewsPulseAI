"""
Abstract base class for all news ingesters.

Every source-specific ingester (NYT, Tavily, Reddit) inherits from
BaseIngester and implements ``fetch()`` and ``source_name``.
"""

from abc import ABC, abstractmethod

from app.schemas.article import RawArticle


class BaseIngester(ABC):
    """Base class that defines the contract for all news source ingesters."""

    @abstractmethod
    async def fetch(self) -> list[RawArticle]:
        """Fetch articles from the source. Returns normalized RawArticle list."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this source (e.g., 'nyt', 'tavily', 'reddit')."""
        ...

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Whether this ingester is configured and ready to run."""
        ...
