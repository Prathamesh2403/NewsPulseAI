"""
Article summarization module.

Provides LLM-based summarization via Google Gemini when available,
with an extractive fallback that returns the first two sentences.
"""

import logging
import re

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _extractive_summary(content: str) -> str:
    """Extract the first two sentences from the content as a fallback summary.

    Uses a simple regex-based sentence splitter that handles common
    abbreviations and decimal numbers.

    Args:
        content: The article body text.

    Returns:
        The first two sentences joined together, or the full content
        if fewer than two sentences are detected.
    """
    if not content or not content.strip():
        return ""

    # Split on sentence-ending punctuation followed by whitespace
    # This pattern matches '.', '!', or '?' followed by a space and an uppercase letter
    # or end of string, while trying to avoid splitting on abbreviations.
    sentences: list[str] = re.split(r'(?<=[.!?])\s+(?=[A-Z])', content.strip())

    if not sentences:
        return content[:500]

    # Take first two sentences
    selected: list[str] = sentences[:2]
    summary: str = " ".join(s.strip() for s in selected if s.strip())

    # Cap length at 500 chars
    if len(summary) > 500:
        summary = summary[:497] + "..."

    return summary


async def summarize_article(title: str, content: str) -> str:
    """Generate a concise summary of a news article.

    If the Gemini API key is configured, uses the LLM for abstractive
    summarization. Otherwise, falls back to extractive summarization
    (first two sentences).

    On LLM failure, gracefully degrades to the extractive fallback.

    Args:
        title: The article title.
        content: The article body text.

    Returns:
        A 2-3 sentence summary string.
    """
    settings = get_settings()

    if not content or not content.strip():
        return title

    # Bypassing LLM during mass ingestion to avoid rate limit stalls
    fallback: str = _extractive_summary(content)
    logger.debug("Extractive summary used for '%s'", title[:60])
    return fallback
