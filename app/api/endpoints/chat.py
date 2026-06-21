"""
Chat endpoint with true token-by-token SSE streaming.

Architecture:
  Phase 1: router_node() — awaited, not streamed (its JSON is internal)
  Phase 2: retrieval_node() — awaited, not streamed
  Phase 3: live_search_node() — conditionally awaited if retrieval is weak
  Phase 4: stream_with_fallback() — only this produces SSE token events

This ensures exactly ONE stream writes to the response.
"""

import json
import logging

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream RAG response tokens via Server-Sent Events."""

    async def event_generator():
        try:
            from app.rag.nodes.router_node import router_node
            from app.rag.nodes.retrieval_node import retrieval_node
            from app.rag.nodes.live_search_node import live_search_node
            from app.rag.prompts.qa_prompt import QA_SYSTEM_PROMPT, QA_USER_TEMPLATE
            from app.rag.prompts.digest_prompt import DIGEST_SYSTEM_PROMPT, DIGEST_USER_TEMPLATE
            from app.core.llm import stream_with_fallback
            from langchain_core.messages import HumanMessage, SystemMessage

            # ── Phase 1: Router (awaited — output is consumed, NOT streamed) ──
            state = {
                "query": request.query,
                "chat_history": request.chat_history or [],
                "route": "",
                "filters": {},
                "retrieved_articles": [],
                "live_search_results": [],
                "response": "",
                "citations": [],
            }
            router_result = await router_node(state)
            state.update(router_result)

            route = state.get("route", "qa")

            # ── Phase 2: Retrieval (awaited — output is consumed, NOT streamed) ──
            retrieval_result = await retrieval_node(state)
            state.update(retrieval_result)

            articles = state.get("retrieved_articles", [])
            
            # ── Phase 3: Live Search Fallback (if QA and retrieval is weak) ──
            if route == "qa":
                top_distance = articles[0].get("distance", 0.0) if articles else 0.0
                if not articles or top_distance > 0.8:
                    logger.info("Retrieval weak (dist: %f), triggering live search", top_distance)
                    live_search_result = await live_search_node(state)
                    state.update(live_search_result)
                    # If live search found something, use it instead of the weak vector results
                    if state.get("live_search_results"):
                        articles = state.get("live_search_results", [])
                        
            if not articles:
                yield f"event: token\ndata: {json.dumps({'text': 'I could not find any relevant articles. Try rephrasing your query.'})}\n\n"
                yield f"event: citations\ndata: {json.dumps({'citations': []})}\n\n"
                yield f"event: done\ndata: {{}}\n\n"
                return

            # Cap articles
            articles = articles[:5] if route == "digest" else articles[:3]

            # ── Phase 4: Build prompt ──
            context_str = ""
            for i, article in enumerate(articles):
                title = article.get("title", "Untitled")
                content_text = article.get("content", "") or article.get("summary", "")
                if len(content_text) > 2000:
                    content_text = content_text[:2000] + "..."
                context_str += f"Article {i+1}:\nTitle: {title}\nContent: {content_text}\n\n"

            chat_history = request.chat_history or []
            history_str = ""
            if chat_history:
                for msg in chat_history[-6:]:
                    role = "User" if msg.get("role", "") == "user" else "Assistant"
                    history_str += f"{role}: {msg.get('content', '')}\n"

            if route == "digest":
                filters = state.get("filters", {})
                category = filters.get("category", "All categories")
                date_from = filters.get("date_from", "")
                date_to = filters.get("date_to", "")
                if date_from and date_to:
                    timeframe = f"{date_from} to {date_to}"
                elif date_from:
                    timeframe = f"From {date_from}"
                elif date_to:
                    timeframe = f"Until {date_to}"
                else:
                    timeframe = "Recent"

                system_prompt = DIGEST_SYSTEM_PROMPT
                user_content = DIGEST_USER_TEMPLATE.format(
                    context=context_str,
                    category=category,
                    timeframe=timeframe,
                )
            else:
                system_prompt = QA_SYSTEM_PROMPT.replace("{context}", context_str).replace("{chat_history}", history_str)
                user_content = QA_USER_TEMPLATE.format(query=request.query)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content),
            ]

            # ── Phase 5: Stream generation — the ONLY thing producing SSE tokens ──
            async for token in stream_with_fallback(messages, temperature=0.3):
                if token:
                    yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

            # ── Phase 6: Citations ──
            citations = [
                {
                    "id": a.get("id", ""),
                    "title": a.get("title", ""),
                    "source": a.get("source", ""),
                    "source_name": a.get("source_name", ""),
                    "url": a.get("url", ""),
                    "published_at": a.get("published_at", ""),
                }
                for a in articles[:3]
            ]
            yield f"event: citations\ndata: {json.dumps({'citations': citations})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"

        except Exception as exc:
            logger.exception("Error during chat streaming")
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


@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(request: ChatRequest) -> ChatResponse:
    """Non-streaming chat endpoint."""
    try:
        from app.rag.graph import get_rag_graph
        graph = get_rag_graph()
        result = await graph.ainvoke({
            "query": request.query,
            "chat_history": request.chat_history or [],
        })
        return ChatResponse(
            response=result.get("response", ""),
            route=result.get("route", "qa"),
            citations=result.get("citations", [])[:3],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat sync error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

