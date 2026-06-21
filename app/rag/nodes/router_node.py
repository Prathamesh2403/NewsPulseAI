"""
Router node for the RAG graph.

Uses Gemini LLM to classify the user's query into one of three
routes (qa, digest, trend) and extract optional metadata filters
such as category, date range, and source.
"""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.core.exceptions import RAGError
from app.rag.prompts.router_prompt import ROUTER_SYSTEM_PROMPT, ROUTER_USER_TEMPLATE
from app.rag.state import RAGState

logger = logging.getLogger(__name__)

# Valid values for validation
_VALID_ROUTES = {"qa", "digest", "trend"}
_VALID_CATEGORIES = {
    "LLMs",
    "Hardware/Chips",
    "Robotics",
    "Startups/Funding",
    "Policy/Regulation",
    "Research",
    "Industry News",
}
_VALID_SOURCES = {"nyt", "tavily", "reddit"}


def _sanitize_filters(raw_filters: Any) -> dict[str, Any]:
    """Validate and sanitize extracted filters.

    Ensures only known filter keys with valid values are kept.
    Invalid or null values are dropped.

    Args:
        raw_filters: The raw filter dict parsed from LLM JSON output.

    Returns:
        A sanitized filter dict with only valid, non-null entries.
    """
    if not isinstance(raw_filters, dict):
        return {}

    sanitized: dict[str, Any] = {}

    category = raw_filters.get("category")
    if category and isinstance(category, str) and category in _VALID_CATEGORIES:
        sanitized["category"] = category

    date_from = raw_filters.get("date_from")
    if date_from and isinstance(date_from, str):
        sanitized["date_from"] = date_from

    date_to = raw_filters.get("date_to")
    if date_to and isinstance(date_to, str):
        sanitized["date_to"] = date_to

    source = raw_filters.get("source")
    if source and isinstance(source, str) and source in _VALID_SOURCES:
        sanitized["source"] = source

    return sanitized


def _parse_router_response(text: str) -> tuple[str, dict[str, Any]]:
    """Extract route and filters from the LLM's JSON response.

    Handles cases where the LLM wraps JSON in markdown code fences
    or includes extra whitespace.

    Args:
        text: Raw text response from the LLM.

    Returns:
        Tuple of (route, sanitized_filters).
    """
    cleaned = text.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    parsed = json.loads(cleaned)

    route = parsed.get("route", "qa")
    if route not in _VALID_ROUTES:
        route = "qa"

    filters = _sanitize_filters(parsed.get("filters", {}))

    return route, filters


async def router_node(state: RAGState) -> dict[str, Any]:
    """Classify the user query and extract filters using Gemini.

    This is the entry-point node of the RAG graph. It sends the
    user's query to the LLM with the router system prompt and
    parses the structured JSON response.

    Falls back to route='qa' with empty filters if LLM output
    cannot be parsed.

    Args:
        state: Current RAG graph state containing at least 'query'.

    Returns:
        Partial state update with 'route' and 'filters' keys.
    """
    query = state.get("query", "")
    logger.info("Router node processing query: %s", query[:100])

    settings = get_settings()
    if not settings.is_llm_enabled:
        logger.warning("Gemini API key not configured — defaulting to route='qa'")
        return {"route": "qa", "filters": {}}

    try:
        from app.core.llm import invoke_gemini_with_fallback

        # Include recent chat history for follow-up context
        chat_history = state.get("chat_history", [])
        history_context = ""
        if chat_history:
            recent = chat_history[-6:]  # last 3 exchanges
            history_lines = []
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]
                history_lines.append(f"{role}: {content}")
            history_context = "\n\nRecent conversation:\n" + "\n".join(history_lines)

        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=ROUTER_USER_TEMPLATE.format(query=query) + history_context),
        ]

        response = await invoke_gemini_with_fallback(messages, temperature=0.0)
        response_text = response.content if hasattr(response, "content") else str(response)

        logger.debug("Router LLM response: %s", response_text[:200])

        route, filters = _parse_router_response(response_text)
        logger.info("Routed to '%s' with filters: %s", route, filters)

        return {"route": route, "filters": filters}

    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse router JSON response, falling back to 'qa': %s",
            exc,
        )
        return {"route": "qa", "filters": {}}

    except Exception as exc:
        logger.warning("Router node error, falling back to 'qa': %s", exc)
        return {"route": "qa", "filters": {}}
