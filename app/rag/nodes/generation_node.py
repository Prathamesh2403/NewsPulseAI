"""
Generation node for the RAG graph.

Constructs a context window from retrieved articles and sends the
grounded QA prompt to Gemini.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.core.exceptions import RAGError
from app.rag.prompts.qa_prompt import QA_SYSTEM_PROMPT, QA_USER_TEMPLATE
from app.rag.state import RAGState

logger = logging.getLogger(__name__)


async def generation_node(state: RAGState) -> dict[str, Any]:
    """Generate a grounded Q&A response with citations.

    Builds a numbered context from retrieved articles, sends the
    QA prompt to Gemini, and extracts which articles were cited.

    Args:
        state: Current RAG graph state with 'query' and 'retrieved_articles'.

    Returns:
        Partial state update with 'response' and 'citations'.
    """
    query = state.get("query", "")
    retrieved_articles = state.get("retrieved_articles", [])

    logger.info(
        "Generation node: answering query with %d articles",
        len(retrieved_articles),
    )

    if not retrieved_articles:
        return {
            "response": (
                "I couldn't find any relevant articles to answer your question. "
                "Try rephrasing your query or broadening the filters."
            ),
            "citations": [],
        }

    # Cap to top 3
    retrieved_articles = retrieved_articles[:3]

    try:
        from app.core.llm import invoke_gemini_with_fallback
        
        # Format context without source labels
        context_str = ""
        for i, article in enumerate(retrieved_articles):
            context_str += f"Article {i+1}:\n"
            context_str += f"Title: {article.get('title', 'Untitled')}\n"
            content_text = article.get('content', '') or article.get('summary', '')
            
            max_content_len = 2000
            if len(content_text) > max_content_len:
                content_text = content_text[:max_content_len] + "..."
                
            context_str += f"Content: {content_text}\n\n"

        # Build chat history context
        chat_history = state.get("chat_history", [])
        history_str = ""
        if chat_history:
            for msg in chat_history[-6:]:  # last 3 exchanges only
                role = "User" if msg.get("role", "") == "user" else "Assistant"
                history_str += f"{role}: {msg.get('content', '')}\n"

        # Replace placeholders directly (prompt has {context} and {chat_history} tokens)
        system_prompt = QA_SYSTEM_PROMPT.replace("{context}", context_str).replace("{chat_history}", history_str)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=QA_USER_TEMPLATE.format(query=query)),
        ]

        # Note: We rely on the stream to generate the output in the streaming handler,
        # but for the state we invoke it to get the final full response string.
        # However, since the endpoint does streaming, the full response here is only used for non-streaming sync calls.
        response = await invoke_gemini_with_fallback(messages, temperature=0.3)
        response_text = response.content if hasattr(response, "content") else str(response)

        # Build citations directly from the retrieved articles metadata
        citations = [
            {
                "id": a.get("id", ""),
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "source_name": a.get("source_name", ""),
                "url": a.get("url", ""),
                "published_at": a.get("published_at", "")
            }
            for a in retrieved_articles
        ]

        logger.info(
            "Generation complete: %d chars, %d citations",
            len(response_text),
            len(citations),
        )

        return {"response": response_text, "citations": citations}

    except Exception as exc:
        logger.warning("Generation node LLM error, using fallback: %s", exc)
        # Build a simple extractive response from retrieved articles
        fallback_parts = ["Here are the most relevant articles I found:\n"]
        citations = []
        for i, article in enumerate(retrieved_articles, 1):
            title = article.get("title", "Untitled")
            source = article.get("source_name", article.get("source", ""))
            summary = article.get("content", "")[:200]
            url = article.get("url", "")
            fallback_parts.append(f"{i}. **{title}** ({source})\n   {summary}...\n")
            citations.append({
                "id": article.get("id", ""),
                "title": title, "url": url,
                "source": article.get("source", ""),
                "source_name": source,
                "published_at": article.get("published_at", ""),
            })
        return {"response": "\n".join(fallback_parts), "citations": citations}
