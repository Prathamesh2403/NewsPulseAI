"""
Embedding generation module.

In DEVELOPMENT: Uses SentenceTransformers with all-MiniLM-L6-v2 (384-dim)
                loaded locally — fast and free.
In PRODUCTION:  Uses Google Gemini text-embedding-004 API (768-dim) — zero
                RAM overhead, no model download, works within Render's 512 MB
                free tier.

The active backend is selected once at startup based on ENVIRONMENT.
"""

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Local (development) model singleton ──────────────────────────────────────
_local_model: Any = None
_local_load_failed: bool = False

# ── Gemini (production) client singleton ─────────────────────────────────────
_gemini_client: Any = None
_gemini_load_failed: bool = False

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_EMBEDDING_DIM = 768
# Gemini embed_content API hard limit: max 100 texts per batch call
# Free tier is limited to 100 requests (texts) per minute.
GEMINI_BATCH_SIZE = 20


def _get_local_model() -> Any:
    """Lazy-load the SentenceTransformer model (development only)."""
    global _local_model, _local_load_failed

    if _local_model is not None:
        return _local_model
    if _local_load_failed:
        return None

    try:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        _local_model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model '%s' loaded successfully", settings.embedding_model)
        return _local_model

    except Exception as exc:
        _local_load_failed = True
        logger.error(
            "Failed to load local embedding model: %s. "
            "Embedding generation will return empty vectors.",
            exc,
        )
        return None


def _get_gemini_client() -> Any:
    """Lazy-load the Google GenAI client (production only).

    Uses the new `google.genai` SDK (v1 API) which supports
    text-embedding-004 and batched embedContent calls.
    """
    global _gemini_client, _gemini_load_failed

    if _gemini_client is not None:
        return _gemini_client
    if _gemini_load_failed:
        return None

    try:
        from google import genai

        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key)
        _gemini_client = client
        logger.info(
            "Gemini embedding client configured (model: %s)", GEMINI_EMBEDDING_MODEL
        )
        return _gemini_client

    except Exception as exc:
        _gemini_load_failed = True
        logger.error(
            "Failed to configure Gemini embedding client: %s. "
            "Embedding generation will return empty vectors.",
            exc,
        )
        return None


# ── Public helpers ────────────────────────────────────────────────────────────

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

    Automatically selects the backend based on ENVIRONMENT:
    - production  → Gemini API (768-dim, no local model)
    - development → SentenceTransformer local model (384-dim)

    Args:
        texts: A list of text strings to embed.

    Returns:
        A list of embedding vectors (each a list of floats).
        Returns empty lists on failure.
    """
    if not texts:
        return []

    settings = get_settings()

    if settings.environment == "production":
        return _generate_gemini_embeddings(texts)
    else:
        return _generate_local_embeddings(texts)


def _generate_local_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using the local SentenceTransformer model."""
    model = _get_local_model()

    if model is None:
        logger.warning("Local embedding model not available, returning empty embeddings")
        return [[] for _ in texts]

    try:
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        result: list[list[float]] = embeddings.tolist()
        logger.debug("Generated %d local embeddings", len(result))
        return result

    except Exception as exc:
        logger.error("Local embedding generation failed: %s", exc)
        return [[] for _ in texts]


def _generate_gemini_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via the Gemini API (production, zero RAM cost).

    Uses the new google.genai SDK (v1 API) with gemini-embedding-001.
    Automatically chunks input into batches of GEMINI_BATCH_SIZE (20)
    because the API limits free tier to 100 texts per minute.
    """
    client = _get_gemini_client()

    if client is None:
        logger.warning("Gemini embedding client not available, returning empty embeddings")
        return [[] for _ in texts]

    try:
        from google.genai import types
        import time

        all_results: list[list[float]] = []

        # Split into chunks of at most GEMINI_BATCH_SIZE to respect API limits
        for batch_start in range(0, len(texts), GEMINI_BATCH_SIZE):
            if batch_start > 0:
                # Sleep to stay under the 100 requests per minute limit
                # 20 items * 5 batches = 100 items. Sleep 15s between 20-item batches
                # ensures we never exceed ~80 items per rolling minute.
                logger.debug("Sleeping for 15s to respect Gemini rate limits...")
                time.sleep(15)

            batch = texts[batch_start : batch_start + GEMINI_BATCH_SIZE]
            
            # Simple retry logic for 429 Resource Exhausted
            retries = 3
            for attempt in range(retries):
                try:
                    response = client.models.embed_content(
                        model=GEMINI_EMBEDDING_MODEL,
                        contents=batch,
                        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                    )
                    all_results.extend(e.values for e in response.embeddings)
                    logger.debug(
                        "Embedded batch %d-%d (%d items)",
                        batch_start,
                        batch_start + len(batch) - 1,
                        len(batch),
                    )
                    break # Success, break out of retry loop
                except Exception as e:
                    if "429" in str(e) and attempt < retries - 1:
                        wait_time = 30 * (attempt + 1)
                        logger.warning("Gemini 429 Rate Limit hit. Retrying in %ds...", wait_time)
                        time.sleep(wait_time)
                    else:
                        raise e

        logger.info("Generated %d Gemini embeddings total", len(all_results))
        return all_results

    except Exception as exc:
        logger.error("Gemini embedding generation failed: %s", exc)
        # Pad with empty arrays if failed halfway so indices still line up
        while len(all_results) < len(texts):
            all_results.append([])
        return all_results


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
