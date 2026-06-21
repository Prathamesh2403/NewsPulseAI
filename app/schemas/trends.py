"""
Pydantic schemas for trend/digest/health API responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Trends ---

class CategoryCount(BaseModel):
    """Article count for a single category."""

    category: str
    count: int


class SentimentBreakdown(BaseModel):
    """Sentiment distribution for a category or overall."""

    positive: int = 0
    neutral: int = 0
    negative: int = 0


class TrendData(BaseModel):
    """Aggregated trend statistics."""

    categories: list[CategoryCount] = Field(default_factory=list)
    sentiment: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    total_articles: int = 0
    timeframe: str = ""  # e.g., "last 7 days"
    summary: Optional[str] = None  # LLM-generated interpretation


class TrendsResponse(BaseModel):
    """API response for the /trends endpoint."""

    data: TrendData
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Digest ---

class DigestItem(BaseModel):
    """A single article summary in the digest."""

    title: str
    summary: str
    url: str
    source: str
    source_name: str = ""
    category: Optional[str] = None
    published_at: Optional[datetime] = None


class DigestResponse(BaseModel):
    """API response for the /digest endpoint."""

    digest: list[DigestItem] = Field(default_factory=list)
    category: Optional[str] = None
    date: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Health ---

class HealthResponse(BaseModel):
    """API response for the /health endpoint."""

    status: str = "ok"
    database: str = "unknown"
    vector_store: str = "unknown"
    vector_store_count: int = 0
    last_ingestion: Optional[datetime] = None
    total_articles: int = 0
