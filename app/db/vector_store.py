"""
ChromaDB vector store client wrapper.

Manages two persistent ChromaDB collections:
- 'articles': embeddings for news articles
- 'community_comments': embeddings for community discussions (HN, Reddit, DevTo)
"""

import logging
from typing import Any

import chromadb

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Wrapper around ChromaDB persistent client for article embeddings."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="articles",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB initialized at %s (collection count: %d)",
            settings.chroma_persist_dir,
            self._collection.count(),
        )

    @property
    def collection(self) -> chromadb.Collection:
        return self._collection

    def upsert_articles(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Upsert article embeddings into the collection."""
        if not ids:
            return
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Upserted %d articles into ChromaDB", len(ids))

    def query_similar(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query the collection for similar articles."""
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self._collection.query(**kwargs)

    def get_stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        return {
            "total_documents": self._collection.count(),
            "collection_name": self._collection.name,
        }


class CommunityVectorStore:
    """Wrapper around ChromaDB for community comment embeddings.
    
    ChromaDB document IDs = str(CommunityComment.id) from Postgres,
    keeping the two stores always in sync.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="community_comments",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Community ChromaDB collection initialized (count: %d)",
            self._collection.count(),
        )

    @property
    def collection(self) -> chromadb.Collection:
        return self._collection

    def upsert_comments(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Upsert community comment embeddings."""
        if not ids:
            return
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Upserted %d community comments into ChromaDB", len(ids))

    def query_similar(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query community comments by semantic similarity."""
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self._collection.query(**kwargs)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_documents": self._collection.count(),
            "collection_name": self._collection.name,
        }


# Module-level singletons
_vector_store: VectorStore | None = None
_community_vector_store: CommunityVectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create the singleton VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_community_vector_store() -> CommunityVectorStore:
    """Get or create the singleton CommunityVectorStore instance."""
    global _community_vector_store
    if _community_vector_store is None:
        _community_vector_store = CommunityVectorStore()
    return _community_vector_store
