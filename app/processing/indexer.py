"""
Dual-write indexer for PostgreSQL and ChromaDB.

Processes raw articles through the full enrichment pipeline:
classify → summarize → sentiment → embed → persist to both stores.
Only new articles from the current ingestion run are processed (incremental).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.db.models import Article
from app.db.session import async_session_factory
from app.db.vector_store import get_vector_store
from app.processing.classifier import classify_article
from app.processing.embedder import generate_embeddings, prepare_embedding_text
from app.processing.sentiment import analyze_sentiment
from app.processing.summarizer import summarize_article
from app.schemas.article import RawArticle

logger = logging.getLogger(__name__)


async def index_articles(articles: list[RawArticle]) -> int:
    """Process and index a batch of raw articles.

    For each article:
        1. Classify into topic category
        2. Generate summary (LLM or extractive fallback)
        3. Analyze sentiment
        4. Generate embedding
        5. Upsert to PostgreSQL (on URL conflict → update)
        6. Upsert to ChromaDB (embeddings + flat metadata)

    Args:
        articles: List of normalized RawArticle objects from ingestion.

    Returns:
        Number of successfully indexed articles.
    """
    if not articles:
        return 0

    logger.info("Processing %d articles for indexing", len(articles))
    indexed_count = 0

    # ── Step 1: Classify all articles ──────────────────────────────────
    categories: list[str] = []
    for a in articles:
        try:
            cat = classify_article(a.title, a.content)
            categories.append(cat)
        except Exception as e:
            logger.warning("Classification failed for '%s': %s", a.title[:50], e)
            categories.append("Other")

    logger.info("Classification complete for %d articles", len(categories))

    # ── Step 2: Summarize all articles ─────────────────────────────────
    import asyncio
    
    async def safe_summarize(a: RawArticle) -> str:
        try:
            return await summarize_article(a.title, a.content)
        except Exception as e:
            logger.warning("Summarization failed for '%s': %s", a.title[:50], e)
            return a.content[:200] if a.content else ""
            
    summaries: list[str] = await asyncio.gather(*(safe_summarize(a) for a in articles))

    logger.info("Summarization complete for %d articles", len(summaries))

    # ── Step 3: Sentiment analysis ─────────────────────────────────────
    sentiments: list[tuple[str, float]] = []
    for a in articles:
        try:
            text = f"{a.title} {a.content[:500]}"
            label, score = analyze_sentiment(text)
            sentiments.append((label, score))
        except Exception as e:
            logger.warning("Sentiment analysis failed for '%s': %s", a.title[:50], e)
            sentiments.append(("neutral", 0.0))

    logger.info("Sentiment analysis complete for %d articles", len(sentiments))

    # ── Step 4: Generate embeddings (batch) ────────────────────────────
    embedding_texts = [
        prepare_embedding_text(a.title, summaries[i], a.content)
        for i, a in enumerate(articles)
    ]
    try:
        embeddings = generate_embeddings(embedding_texts)
    except Exception as e:
        logger.error("Batch embedding generation failed: %s", e)
        return 0

    logger.info("Generated %d embeddings", len(embeddings))

    # ── Steps 5 & 6: Prepare records for both stores ──────────────────
    db_records: list[dict] = []
    chroma_ids: list[str] = []
    chroma_embeddings: list[list[float]] = []
    chroma_documents: list[str] = []
    chroma_metadatas: list[dict] = []

    for i, article in enumerate(articles):
        try:
            sentiment_label, sentiment_score = sentiments[i]
            embedding_id = article.id

            # Prepare PostgreSQL record
            # DEV: store source URL directly as image_url (no Supabase for now)
            source_image = article.image_url or (article.raw_metadata or {}).get("image_url") or None
            db_records.append(
                {
                    "id": article.id,
                    "title": article.title,
                    "content": article.content,
                    "summary": summaries[i],
                    "url": article.url,
                    "source": article.source,
                    "source_name": article.source_name,
                    "category": categories[i],
                    "sentiment_label": sentiment_label,
                    "sentiment_score": sentiment_score,
                    "published_at": article.published_at,
                    "fetched_at": article.fetched_at or datetime.now(timezone.utc),
                    "embedding_id": embedding_id,
                    "raw_metadata": article.raw_metadata,
                    "image_url": source_image,
                    "image_url_original": source_image,
                }
            )

            # Prepare ChromaDB record (metadata must be flat: str/int/float/bool)
            chroma_ids.append(embedding_id)
            chroma_embeddings.append(embeddings[i])
            chroma_documents.append(embedding_texts[i][:5000])
            chroma_metadatas.append(
                {
                    "category": categories[i] or "Other",
                    "source": article.source,
                    "source_name": article.source_name or "",
                    "published_at": (
                        article.published_at.isoformat()
                        if article.published_at
                        else ""
                    ),
                    "sentiment_label": sentiment_label,
                    "sentiment_score": sentiment_score,
                    "title": article.title[:500],
                    "url": article.url,
                }
            )

            indexed_count += 1
        except Exception as e:
            logger.error(
                "Failed to prepare article '%s' for indexing: %s",
                article.title[:50],
                e,
            )

    # ── Write to PostgreSQL ────────────────────────────────────────────
    if db_records:
        try:
            async with async_session_factory() as session:
                for record in db_records:
                    stmt = (
                        insert(Article)
                        .values(**record)
                        .on_conflict_do_update(
                            index_elements=["url"],
                            set_={
                                "title": record["title"],
                                "content": record["content"],
                                "summary": record["summary"],
                                "category": record["category"],
                                "sentiment_label": record["sentiment_label"],
                                "sentiment_score": record["sentiment_score"],
                                "embedding_id": record["embedding_id"],
                                "image_url": record["image_url"],
                                "image_url_original": record["image_url_original"],
                            },
                        )
                    )
                    await session.execute(stmt)
                await session.commit()
            logger.info("Upserted %d records to PostgreSQL", len(db_records))
        except Exception as e:
            logger.error("PostgreSQL upsert failed: %s", e)
            indexed_count = 0

    # ── Write to ChromaDB ──────────────────────────────────────────────
    if chroma_ids:
        try:
            vector_store = get_vector_store()
            vector_store.upsert_articles(
                ids=chroma_ids,
                embeddings=chroma_embeddings,
                documents=chroma_documents,
                metadatas=chroma_metadatas,
            )
            logger.info("Upserted %d embeddings to ChromaDB", len(chroma_ids))
        except Exception as e:
            logger.error("ChromaDB upsert failed: %s", e)

    logger.info(
        "Indexing complete: %d/%d articles processed successfully",
        indexed_count,
        len(articles),
    )
    return indexed_count
