"""
Embedding generation module.

Uses SentenceTransformers with the all-MiniLM-L6-v2 model to produce
384-dimensional dense vector embeddings for articles and queries.

The model is lazy-loaded as a module-level singleton to avoid reloading
on every call.
"""

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton for the embedding model
_embedding_model: Any = None
_model_load_failed: bool = False


def _get_model() -> Any:
    """Lazy-load the SentenceTransformer embedding model.

    Returns the model instance on success, or None if loading fails.
    Once loading fails, subsequent calls return None immediately.

    Returns:
        The SentenceTransformer model instance, or None on failure.
    """
    global _embedding_model, _model_load_failed

    if _embedding_model is not None:
        return _embedding_model

    if _model_load_failed:
        return None

    try:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info(
            "Embedding model '%s' loaded successfully", settings.embedding_model
        )
        return _embedding_model

    except Exception as exc:
        _model_load_failed = True
        logger.error(
            "Failed to load embedding model: %s. "
            "Embedding generation will return empty vectors.",
            exc,
        )
        return None


def prepare_embedding_text(
    title: str, summary: str | None = None, content: str = ""
) -> str:
    """Prepare text for embedding by combining title, summary, and content.

    Args:
        title: Article title.
        summary: Optional article summary.
        content: Article content (truncated to first 1000 chars).

    Returns:
        Combined text string for embedding.
    """
    parts = [title]
    if summary:
        parts.append(summary)
    if content:
        parts.append(content[:1000])
    return " ".join(parts)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate vector embeddings for a batch of texts.

    Each text should ideally be constructed as:
        title + ' ' + (summary or '') + ' ' + content[:1000]

    Args:
        texts: A list of text strings to embed.

    Returns:
        A list of embedding vectors (each a list of floats).
        Returns empty lists on failure.
    """
    if not texts:
        return []

    model = _get_model()

    if model is None:
        logger.warning("Embedding model not available, returning empty embeddings")
        return [[] for _ in texts]

    try:
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        result: list[list[float]] = embeddings.tolist()
        logger.debug("Generated embeddings for %d texts", len(result))
        return result

    except Exception as exc:
        logger.error("Embedding generation failed: %s", exc)
        return [[] for _ in texts]


def generate_single_embedding(text: str) -> list[float]:
    """Generate a vector embedding for a single text string.

    Convenience wrapper around generate_embeddings for query-time use.

    Args:
        text: The text to embed (e.g. a user query).

    Returns:
        An embedding vector as a list of floats, or an empty list on failure.
    """
    if not text or not text.strip():
        return []

    results: list[list[float]] = generate_embeddings([text])

    if results and results[0]:
        return results[0]

    return []
