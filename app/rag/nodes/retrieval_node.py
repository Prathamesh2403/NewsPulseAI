"""
Retrieval node for the RAG graph.

Generates a query embedding and searches the ChromaDB vector store
for similar articles, applying any metadata filters extracted by
the router node.
"""

import logging
from datetime import datetime
from typing import Any

from app.core.exceptions import RAGError
from app.db.vector_store import get_vector_store
from app.rag.state import RAGState

logger = logging.getLogger(__name__)


def _build_chroma_where_filter(filters: dict[str, Any]) -> dict[str, Any] | None:
    """Translate RAG state filters into a ChromaDB ``where`` clause.

    ChromaDB supports ``$and`` / ``$or`` combinators and operators
    like ``$eq``, ``$gte``, ``$lte`` on metadata fields.

    Args:
        filters: Sanitized filter dict from the router node.

    Returns:
        A ChromaDB-compatible ``where`` dict, or ``None`` if no
        filters apply.
    """
    conditions: list[dict[str, Any]] = []

    category = filters.get("category")
    if category:
        conditions.append({"category": {"$eq": category}})

    source = filters.get("source")
    if source:
        conditions.append({"source": {"$eq": source}})

    # Note: ChromaDB does not support $gte/$lte on string fields like published_at.
    # We handle date filtering in Python after retrieving the documents.

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


def _generate_query_embedding(query: str) -> list[float]:
    """Generate a vector embedding for the query string.

    Uses the same SentenceTransformer model as the ingestion
    pipeline to keep embeddings in the same space.

    Args:
        query: The text to embed.

    Returns:
        A list of floats representing the embedding vector.
    """
    try:
        from app.processing.embedder import generate_single_embedding

        return generate_single_embedding(query)
    except ImportError:
        # Fallback: load model directly when the processing module
        # hasn't been created yet.
        logger.debug(
            "app.processing.embedder not available — loading SentenceTransformer directly"
        )
        from sentence_transformers import SentenceTransformer

        from app.core.config import get_settings

        settings = get_settings()
        model = SentenceTransformer(settings.embedding_model)
        embedding: list[float] = model.encode(query).tolist()
        return embedding


async def retrieval_node(state: RAGState) -> dict[str, Any]:
    """Retrieve similar articles from the vector store.

    Generates an embedding of the user query and queries ChromaDB
    with optional metadata filters.  Returns 10 results for QA
    queries and 20 for digest queries.

    Args:
        state: Current RAG graph state.

    Returns:
        Partial state update with 'retrieved_articles' list.
    """
    query = state.get("query", "")
    route = state.get("route", "qa")
    filters = state.get("filters", {})

    n_results = 20 if route == "digest" else 10

    logger.info(
        "Retrieval node: route=%s, n_results=%d, filters=%s",
        route,
        n_results,
        filters,
    )

    try:
        # Enrich short follow-up queries with context from chat history
        chat_history = state.get("chat_history", [])
        if len(query.split()) < 6 and chat_history:
            last_user_msg = next(
                (m["content"] for m in reversed(chat_history) 
                 if m["role"] == "user"), ""
            )
            search_query = f"{last_user_msg} {query}"
        else:
            search_query = query

        # Generate query embedding
        query_embedding = _generate_query_embedding(search_query)

        # Build ChromaDB where filter
        where_filter = _build_chroma_where_filter(filters)

        # If we have date filters, over-fetch so we can filter in Python
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        fetch_limit = n_results * 5 if (date_from or date_to) else n_results

        # Query the vector store
        vector_store = get_vector_store()
        results = vector_store.query_similar(
            query_embedding=query_embedding,
            n_results=fetch_limit,
            where=where_filter,
        )

        # Parse results into structured article dicts
        articles: list[dict[str, Any]] = []
        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        meta_list = results.get("metadatas", [[]])[0]
        dist_list = results.get("distances", [[]])[0]

        for idx, (doc_id, document, metadata, distance) in enumerate(
            zip(ids_list, docs_list, meta_list, dist_list)
        ):
            pub_date = metadata.get("published_at", "") if metadata else ""
            
            # Apply Python-side date filtering (string comparison works for ISO 8601)
            if date_from or date_to:
                if not pub_date:
                    continue  # exclude articles without dates if filtering by date
                if date_from and pub_date < date_from:
                    continue
                # For date_to, append T23:59:59 to include the whole day if it's just YYYY-MM-DD
                date_to_inclusive = date_to + "T23:59:59" if (date_to and "T" not in date_to) else date_to
                if date_to and pub_date > date_to_inclusive:
                    continue

            article: dict[str, Any] = {
                "id": doc_id,
                "content": document or "",
                "distance": distance,
                "title": metadata.get("title", "Untitled") if metadata else "Untitled",
                "url": metadata.get("url", "") if metadata else "",
                "source": metadata.get("source", "") if metadata else "",
                "source_name": metadata.get("source_name", "") if metadata else "",
                "published_at": pub_date,
                "category": metadata.get("category", "") if metadata else "",
            }
            articles.append(article)
            
            if len(articles) >= n_results:
                break

        logger.info("Retrieved %d articles from vector store", len(articles))
        
        print(f"[RETRIEVAL] Query: {search_query}")
        print(f"[RETRIEVAL] Result count: {len(articles)}")
        if articles:
            print(f"[RETRIEVAL] Best distance: {articles[0].get('distance', 'N/A')}")

        results_are_weak = (
            len(articles) == 0
            or len(articles) < 2
            or (articles[0].get("distance", 1.0) > 0.8)
        )

        use_live_search = bool(results_are_weak)

        return {"retrieved_articles": articles, "use_live_search": use_live_search}

    except Exception as exc:
        logger.error("Retrieval node error: %s", exc, exc_info=True)
        raise RAGError(node="retrieval", message=str(exc)) from exc
