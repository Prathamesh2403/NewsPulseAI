import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models import Article
from app.db.vector_store import get_vector_store
from app.processing.embedder import generate_embeddings, prepare_embedding_text
from app.core.logging import setup_logging

async def reindex_articles():
    setup_logging()
    
    async with async_session_factory() as session:
        result = await session.execute(select(Article))
        articles = result.scalars().all()
        
    print(f"Found {len(articles)} articles in DB to re-index.")
    
    if not articles:
        return
        
    embedding_texts = []
    chroma_ids = []
    chroma_metadatas = []
    
    for article in articles:
        text = prepare_embedding_text(
            title=article.title, summary=article.summary, content=article.content
        )
        embedding_texts.append(text)
        chroma_ids.append(str(article.id))
        chroma_metadatas.append({
            "category": article.category or "Other",
            "source": article.source or "",
            "source_name": article.source_name or "",
            "published_at": article.published_at.isoformat() if article.published_at else "",
            "sentiment_label": article.sentiment_label or "neutral",
            "sentiment_score": article.sentiment_score or 0.0,
            "title": article.title[:500],
            "url": article.url or "",
        })
        
    print("Generating embeddings...")
    embeddings = generate_embeddings(embedding_texts)
    
    # Verify no empty lists
    if not embeddings or not embeddings[0]:
        print("Error: Embeddings are still empty!")
        return
        
    print(f"Upserting {len(embeddings)} vectors into ChromaDB...")
    vector_store = get_vector_store()
    vector_store.upsert_articles(
        ids=chroma_ids,
        embeddings=embeddings,
        documents=[t[:5000] for t in embedding_texts],
        metadatas=chroma_metadatas
    )
    print("Done reindexing articles.")

if __name__ == "__main__":
    asyncio.run(reindex_articles())
