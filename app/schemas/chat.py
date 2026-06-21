"""
Pydantic schemas for chat (RAG) request/response models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User chat message sent to the RAG pipeline."""

    query: str = Field(..., min_length=1, max_length=2000, description="User's question")
    chat_history: list[dict] = Field(default_factory=list, description="Previous messages: [{role, content}]")


class ArticleChatRequest(BaseModel):
    """Chat message scoped to a specific article."""

    query: str = Field(..., min_length=1, max_length=2000)
    chat_history: list[dict] = Field(default_factory=list)


class CitationItem(BaseModel):
    """A single source citation attached to a response."""

    title: str
    url: str
    source: str
    source_name: str = ""
    published_at: Optional[datetime] = None


class ChatResponse(BaseModel):
    """Full chat response returned after streaming completes."""

    response: str
    route: str  # "qa", "digest", "trend"
    citations: list[CitationItem] = Field(default_factory=list)


class StreamEvent(BaseModel):
    """A single SSE event sent during streaming."""

    event: str  # "token", "citation", "done", "error"
    data: str   # JSON-encoded payload
