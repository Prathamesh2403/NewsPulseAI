"""
Pydantic schemas for articles.

Used across ingestion, processing, and API layers for consistent
data validation and serialization.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class RawArticle(BaseModel):
    """Normalized article from any ingestion source, before processing."""

    id: str = Field(..., description="Deterministic hash of url+title")
    title: str
    content: str
    url: str
    source: str = Field(..., description="Source type: newsdata, newsapi, apitube")
    source_name: str = Field(default="", description="e.g. 'TechCrunch'")
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    image_url: Optional[str] = None


class ArticleCreate(BaseModel):
    """Schema for creating/updating an article in the database."""

    id: str
    title: str
    content: str
    summary: Optional[str] = None
    url: str
    source: str
    source_name: str = ""
    category: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_id: Optional[str] = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    image_url: Optional[str] = None
    image_url_original: Optional[str] = None


class ArticleResponse(BaseModel):
    """Article data returned by the API."""

    id: str
    title: str
    content: str
    summary: Optional[str] = None
    url: str
    source: str
    source_name: str = ""
    category: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    image_url: Optional[str] = None
    image_url_original: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleSummaryResponse(BaseModel):
    """Compact article for list views and featured sidebar."""

    id: str
    title: str
    summary: Optional[str] = None
    url: str
    source: str
    source_name: str = ""
    category: Optional[str] = None
    sentiment_label: Optional[str] = None
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    """Paginated list of articles."""

    articles: list[ArticleSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
