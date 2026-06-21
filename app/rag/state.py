"""
LangGraph state definition for the RAG pipeline.

Defines the shared state schema that flows between all nodes
in the agentic RAG graph.
"""

from typing import Optional, TypedDict


class RAGState(TypedDict, total=False):
    """Typed state dictionary shared across all LangGraph nodes."""

    query: str
    route: str
    filters: dict
    retrieved_articles: list
    live_search_results: list
    response: str
    citations: list
    chat_history: list
