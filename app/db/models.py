"""
SQLAlchemy ORM models for the application.

Three main tables:
- Article: stores processed news articles (news sources ONLY)
- CommunityComment: independent store for community discussions (HN, Reddit, DevTo)
- IngestionRun: logs each ingestion pipeline execution for observability
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.db.session import Base


class Article(Base):
    """Represents a processed news article stored in PostgreSQL.
    
    ONLY news sources (Newsdata.io, NewsAPI.ai, ApiTube) go here.
    Community posts (HN, Reddit, DevTo) go in CommunityComment.
    """

    __tablename__ = "articles"

    id = Column(String(128), primary_key=True)  # SHA256 hex hash of url+title
    title = Column(String(1024), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String(2048), nullable=False, unique=True, index=True)
    source = Column(String(50), nullable=False, index=True)       # "newsdata", "newsapi", "apitube"
    source_name = Column(String(256), nullable=True)               # e.g., "TechCrunch", "Reuters"
    category = Column(String(100), nullable=True, index=True)      # "LLMs", "Robotics", etc.
    sentiment_label = Column(String(20), nullable=True, index=True) # "positive", "neutral", "negative"
    sentiment_score = Column(Float, nullable=True)                  # -1.0 to 1.0
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    embedding_id = Column(String(256), nullable=True)  # ChromaDB document ID
    raw_metadata = Column(JSON, nullable=True)          # Original source-specific fields

    # Image fields
    image_url = Column(String(2048), nullable=True)           # in dev = source URL, in prod = Supabase URL
    image_url_original = Column(String(2048), nullable=True)  # always = source URL

    # Feature flag
    is_featured = Column(Boolean, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<Article(title='{self.title[:50]}...', source='{self.source}')>"


class CommunityComment(Base):
    """Independent store for community discussions (HN, Reddit, DEV.to).
    
    NOT linked to articles via FK. ChromaDB uses str(id) as its document ID,
    keeping Postgres and ChromaDB always in sync.
    """

    __tablename__ = "community_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, index=True)  # "hackernews", "reddit", "devto"
    username = Column(String(256), nullable=False)
    body = Column(Text, nullable=False)
    url = Column(String(2048), nullable=True)
    upvotes = Column(Integer, default=0)
    topic_tags = Column(JSON, nullable=True)  # ["LLMs", "Hardware"]
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<CommunityComment(platform='{self.platform}', user='{self.username}')>"


class IngestionRun(Base):
    """Logs each ingestion pipeline execution for observability."""

    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="running")  # "running" | "success" | "failed"
    new_articles = Column(Integer, nullable=False, default=0)
    community_items = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    sources_breakdown = Column(JSON, nullable=True)  # e.g. {"newsdata": 12, "newsapi": 8, "hackernews": 5}

    def __repr__(self) -> str:
        return f"<IngestionRun(status='{self.status}', new_articles={self.new_articles}, community_items={self.community_items})>"
