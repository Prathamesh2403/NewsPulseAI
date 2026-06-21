"""
Digest node for the RAG graph.

Takes retrieved articles and sends them through the digest prompt
to produce a structured, categorised news summary.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.core.exceptions import RAGError
from app.rag.prompts.digest_prompt import DIGEST_SYSTEM_PROMPT, DIGEST_USER_TEMPLATE
from app.rag.state import RAGState

logger = logging.getLogger(__name__)


def _build_digest_context(articles: list[dict[str, Any]]) -> str:
    """Format articles into a context block optimised for digest generation.

    Each article includes its title, source, category, publication
    date, and a truncated content snippet.

    Args:
        articles: List of article dicts from the retrieval node.

    Returns:
        Formatted context string.
    """
    if not articles:
        return "(No articles found)"

    parts: list[str] = []
    for idx, article in enumerate(articles, start=1):
        title = article.get("title", "Untitled")
        source_name = article.get("source_name", article.get("source", "Unknown"))
        category = article.get("category", "Uncategorized")
        published_at = article.get("published_at", "Unknown date")
        content = article.get("content", "")

        # Shorter snippets for digests — the LLM summarises anyway
        max_content_len = 1500
        if len(content) > max_content_len:
            content = content[:max_content_len] + "..."

        block = (
            f"Article {idx}:\n"
            f"Title: {title}\n"
            f"Content: {content}\n"
        )
        parts.append(block)

    return "\n---\n".join(parts)


def _build_all_citations(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build citations for every article in the digest.

    Unlike QA, digests reference all retrieved articles.

    Args:
        articles: List of article dicts.

    Returns:
        List of citation dicts.
    """
    citations: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for article in articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            citations.append(
                {
                    "title": article.get("title", "Untitled"),
                    "url": url,
                    "source": article.get("source", ""),
                    "source_name": article.get("source_name", ""),
                    "published_at": article.get("published_at", ""),
                }
            )

    return citations


async def digest_node(state: RAGState) -> dict[str, Any]:
    """Generate a structured news digest from retrieved articles.

    Formats articles into context, sends the digest prompt to
    Gemini, and returns the formatted digest with full citations.

    Args:
        state: Current RAG graph state.

    Returns:
        Partial state update with 'response' and 'citations'.
    """
    articles = state.get("retrieved_articles", [])
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

    logger.info(
        "Digest node: %d articles, category=%s, timeframe=%s",
        len(articles),
        category,
        timeframe,
    )

    if not articles:
        return {
            "response": (
                "No articles found matching your digest criteria. "
                "Try broadening the timeframe or category filter."
            ),
            "citations": [],
        }

    settings = get_settings()

    try:
        from app.core.llm import invoke_gemini_with_fallback
        context = _build_digest_context(articles)

        messages = [
            SystemMessage(content=DIGEST_SYSTEM_PROMPT),
            HumanMessage(
                content=DIGEST_USER_TEMPLATE.format(
                    context=context,
                    category=category,
                    timeframe=timeframe,
                )
            ),
        ]

        response = await invoke_gemini_with_fallback(messages, temperature=0.4)
        response_text = response.content if hasattr(response, "content") else str(response)

        citations = _build_all_citations(articles)

        logger.info(
            "Digest complete: %d chars, %d citations",
            len(response_text),
            len(citations),
        )

        return {"response": response_text, "citations": citations}

    except Exception as exc:
        logger.warning("Digest node LLM error, using fallback: %s", exc)
        # Build a simple extractive digest
        fallback_parts = ["## AI/Tech News Digest\n"]
        citations = _build_all_citations(articles)
        for i, article in enumerate(articles[:10], 1):
            title = article.get("title", "Untitled")
            source = article.get("source_name", article.get("source", ""))
            cat = article.get("category", "")
            content = article.get("content", "")[:150]
            fallback_parts.append(
                f"**{i}. {title}** [{cat}] — {source}\n> {content}...\n"
            )
        return {"response": "\n".join(fallback_parts), "citations": citations}
