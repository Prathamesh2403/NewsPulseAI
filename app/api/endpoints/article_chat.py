"""
Article-scoped chat endpoint with SSE streaming.

Allows users to chat about a specific article on its detail page.
Context passed to the LLM includes the article summary and related
community discussions fetched via semantic search from ChromaDB.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage

from app.db.models import Article
from app.db.session import get_db
from app.db.vector_store import get_community_vector_store
from app.schemas.chat import ArticleChatRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

ARTICLE_CHAT_SYSTEM_PROMPT = """You are a helpful AI assistant analyzing a specific tech news article.
You are chatting with a user who is reading the article right now.

Use the following context to answer the user's question. 
The context contains the article's summary, and optionally, relevant community discussions (Reddit, HackerNews, DevTo) related to the topic.

Article Context:
{article_context}

Community Discussion Context:
{community_context}

Chat History:
{chat_history}

Instructions:
1. Answer the user's question concisely based on the provided context.
2. If the user asks about community opinions, refer to the Community Discussion Context.
3. If the answer is not in the context, say you don't know based on the provided info.
4. Keep your responses engaging and directly address the user.
"""


@router.post("/chat/article/{article_id}")
async def article_chat(
    article_id: str,
    request: ArticleChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream article-scoped chat response tokens via Server-Sent Events."""

    # 1. Fetch article from Postgres
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    async def event_generator():
        try:
            from app.core.llm import stream_with_fallback
            from app.processing.embedder import generate_single_embedding

            # 2. Build search query and embed it
            search_query = f"{article.title} {request.query}"
            try:
                query_embedding = generate_single_embedding(search_query)
            except Exception as exc:
                logger.warning("Failed to generate embedding for community search: %s", exc)
                query_embedding = []

            # 3. Search community_comments ChromaDB collection
            community_context = ""
            if query_embedding:
                try:
                    community_store = get_community_vector_store()
                    community_results = community_store.query_similar(
                        query_embedding=query_embedding,
                        n_results=3,
                        where={"platform": {"$in": ["hackernews", "reddit", "devto"]}}
                    )

                    docs = community_results.get("documents", [[]])[0]
                    metas = community_results.get("metadatas", [[]])[0]

                    for doc, meta in zip(docs, metas):
                        platform = meta.get("platform", "community")
                        username = meta.get("username", "anonymous")
                        upvotes = meta.get("upvotes", 0)
                        community_context += f"[{platform} - u/{username} - {upvotes} upvotes]: {doc}\n\n"
                except Exception as exc:
                    logger.warning("Community ChromaDB search failed: %s", exc)

            if not community_context:
                community_context = "No relevant community discussions found."

            # 4. Build LLM prompt
            article_context = f"Title: {article.title}\nSummary: {article.summary or article.content[:1000]}"

            chat_history = request.chat_history or []
            history_str = ""
            if chat_history:
                for msg in chat_history[-4:]:  # last 2 exchanges
                    role = "User" if msg.get("role", "") == "user" else "Assistant"
                    history_str += f"{role}: {msg.get('content', '')}\n"

            system_prompt = ARTICLE_CHAT_SYSTEM_PROMPT.format(
                article_context=article_context,
                community_context=community_context,
                chat_history=history_str,
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=request.query),
            ]

            # 5. Stream response
            async for token in stream_with_fallback(messages, temperature=0.3):
                if token:
                    yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

            yield f"event: done\ndata: {{}}\n\n"

        except Exception as exc:
            logger.exception("Error during article chat streaming")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )

