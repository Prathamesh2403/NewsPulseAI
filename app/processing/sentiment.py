"""
Sentiment analysis module.

Uses a Hugging Face DistilBERT model fine-tuned on SST-2 to classify
article text as positive, neutral, or negative with a confidence score
on a -1.0 to +1.0 scale.

The transformer pipeline is lazy-loaded as a module-level singleton
to avoid reloading the model on every call.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Module-level singleton for the sentiment pipeline
_sentiment_pipeline: Any = None
_pipeline_load_failed: bool = False


def _get_pipeline() -> Any:
    """Lazy-load the Hugging Face sentiment analysis pipeline.

    Returns the pipeline instance on success, or None if loading fails.
    Once loading fails, subsequent calls return None immediately to avoid
    repeated download/initialization attempts.

    In production (Render free tier) the model is skipped entirely to stay
    within the 512 MB RAM limit — sentiment returns neutral defaults instead.

    Returns:
        The transformers Pipeline instance, or None on failure.
    """
    global _sentiment_pipeline, _pipeline_load_failed

    if _sentiment_pipeline is not None:
        return _sentiment_pipeline

    if _pipeline_load_failed:
        return None

    # Skip in production to save ~250 MB RAM on Render's free tier
    from app.core.config import get_settings
    if get_settings().environment == "production":
        logger.info(
            "Production mode — sentiment analysis disabled to reduce RAM usage. "
            "Articles will be stored with neutral sentiment defaults."
        )
        _pipeline_load_failed = True
        return None

    try:
        from transformers import pipeline

        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
        )
        logger.info("Sentiment analysis pipeline loaded successfully")
        return _sentiment_pipeline

    except Exception as exc:
        _pipeline_load_failed = True
        logger.warning(
            "Failed to load sentiment analysis pipeline: %s. "
            "Sentiment analysis will return neutral defaults.",
            exc,
        )
        return None



def analyze_sentiment(text: str) -> tuple[str, float]:
    """Analyze the sentiment of the given text.

    Uses the DistilBERT SST-2 model to classify text and maps the result
    to a three-class label (positive / neutral / negative) with a
    continuous score on a -1.0 to +1.0 scale.

    Mapping logic:
    - Model returns POSITIVE with confidence > 0.7 → ('positive', +confidence)
    - Model returns NEGATIVE with confidence > 0.7 → ('negative', -confidence)
    - Otherwise → ('neutral', ±small_score)

    Input is truncated to ~512 tokens (first 512 whitespace-delimited words)
    to stay within the model's context window.

    Args:
        text: The text to analyze (article title + content).

    Returns:
        A tuple of (label, score) where label is one of
        'positive', 'neutral', 'negative' and score is in [-1.0, 1.0].
    """
    if not text or not text.strip():
        return ("neutral", 0.0)

    pipe = _get_pipeline()

    if pipe is None:
        return ("neutral", 0.0)

    try:
        # Truncate to approximately 512 tokens (using words as proxy)
        words: list[str] = text.split()
        truncated_text: str = " ".join(words[:512])

        result: list[dict[str, Any]] = pipe(truncated_text)
        model_label: str = result[0]["label"]       # "POSITIVE" or "NEGATIVE"
        model_score: float = result[0]["score"]      # 0.0 to 1.0 confidence

        # Map to our three-class system with a -1.0 to 1.0 scale
        if model_label == "POSITIVE" and model_score > 0.7:
            return ("positive", round(model_score, 4))
        elif model_label == "NEGATIVE" and model_score > 0.7:
            return ("negative", round(-model_score, 4))
        else:
            # Neutral zone: preserve direction but mark as neutral
            if model_label == "POSITIVE":
                return ("neutral", round(model_score * 0.5, 4))
            else:
                return ("neutral", round(-model_score * 0.5, 4))

    except Exception as exc:
        logger.warning("Sentiment analysis failed: %s", exc)
        return ("neutral", 0.0)
