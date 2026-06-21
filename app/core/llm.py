"""
LLM provider management with automatic two-tier fallback.

Priority order per request:
  1. Gemini  (primary — uses gemini-2.5-flash via google-genai SDK)
  2. Groq    (fallback — fast inference)

Key behaviours
--------------
- Round-robin across all configured keys for each provider
- 429 / quota errors  → remove that key from the in-memory pool; try next key
- Other errors (5xx)  → do NOT burn the key; propagate and let the caller retry
                        with a different provider
"""

import itertools
import logging
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini key pool (round-robin)
# ---------------------------------------------------------------------------

_gemini_active_keys: list[str] | None = None
_gemini_lock = threading.Lock()
_gemini_iterator: itertools.cycle | None = None


def _load_gemini_keys() -> list[str]:
    from app.core.config import get_settings
    return list(get_settings().all_gemini_keys)


def get_active_gemini_keys() -> list[str]:
    global _gemini_active_keys
    with _gemini_lock:
        if _gemini_active_keys is None:
            _gemini_active_keys = _load_gemini_keys()
        return list(_gemini_active_keys)


def _get_next_gemini_key() -> str:
    """Return the next Gemini API key in round-robin order."""
    global _gemini_iterator
    keys = get_active_gemini_keys()
    if not keys:
        raise RuntimeError("No active Gemini keys.")
    with _gemini_lock:
        if _gemini_iterator is None:
            _gemini_iterator = itertools.cycle(keys)
        return next(_gemini_iterator)


def mark_gemini_key_bad(key: str) -> None:
    """Remove a key from the Gemini pool (quota exhausted)."""
    global _gemini_active_keys, _gemini_iterator
    with _gemini_lock:
        if _gemini_active_keys:
            _gemini_active_keys = [k for k in _gemini_active_keys if k != key]
            _gemini_iterator = itertools.cycle(_gemini_active_keys) if _gemini_active_keys else None
            logger.warning("Gemini key ...%s removed (quota exhausted). %d keys remaining.",
                           key[-4:], len(_gemini_active_keys))
            if not _gemini_active_keys:
                # All quota exhausted — reset so they're retried on next cycle
                _gemini_active_keys = None
                _gemini_iterator = None


# ---------------------------------------------------------------------------
# Groq key pool (round-robin)
# ---------------------------------------------------------------------------

_groq_active_keys: list[str] | None = None
_groq_lock = threading.Lock()
_groq_iterator: itertools.cycle | None = None


def get_active_groq_keys() -> list[str]:
    global _groq_active_keys
    with _groq_lock:
        if _groq_active_keys is None:
            from app.core.config import get_settings
            _groq_active_keys = list(get_settings().all_groq_keys)
        return list(_groq_active_keys)


def _get_next_groq_key() -> str:
    """Return the next Groq API key in round-robin order."""
    global _groq_iterator
    keys = get_active_groq_keys()
    if not keys:
        raise RuntimeError("No active Groq keys.")
    with _groq_lock:
        if _groq_iterator is None:
            _groq_iterator = itertools.cycle(keys)
        return next(_groq_iterator)


def mark_groq_key_bad(key: str) -> None:
    global _groq_active_keys, _groq_iterator
    with _groq_lock:
        if _groq_active_keys:
            _groq_active_keys = [k for k in _groq_active_keys if k != key]
            _groq_iterator = itertools.cycle(_groq_active_keys) if _groq_active_keys else None
            logger.warning("Groq key ...%s removed (quota exhausted). %d keys remaining.",
                           key[-4:], len(_groq_active_keys))
            if not _groq_active_keys:
                _groq_active_keys = None
                _groq_iterator = None


# ---------------------------------------------------------------------------
# Tavily key pool (round-robin)
# ---------------------------------------------------------------------------

_tavily_active_keys: list[str] | None = None
_tavily_lock = threading.Lock()
_tavily_iterator: itertools.cycle | None = None


def get_active_tavily_keys() -> list[str]:
    global _tavily_active_keys
    with _tavily_lock:
        if _tavily_active_keys is None:
            from app.core.config import get_settings
            _tavily_active_keys = list(get_settings().all_tavily_keys)
        return list(_tavily_active_keys)


def get_next_tavily_key() -> str:
    """Return the next Tavily API key in round-robin order."""
    global _tavily_iterator
    keys = get_active_tavily_keys()
    if not keys:
        raise RuntimeError("No active Tavily keys.")
    with _tavily_lock:
        if _tavily_iterator is None:
            _tavily_iterator = itertools.cycle(keys)
        return next(_tavily_iterator)


def mark_tavily_key_bad(key: str) -> None:
    global _tavily_active_keys, _tavily_iterator
    with _tavily_lock:
        if _tavily_active_keys:
            _tavily_active_keys = [k for k in _tavily_active_keys if k != key]
            _tavily_iterator = itertools.cycle(_tavily_active_keys) if _tavily_active_keys else None
            logger.warning("Tavily key ...%s removed. %d keys remaining.",
                           key[-4:], len(_tavily_active_keys))
            if not _tavily_active_keys:
                _tavily_active_keys = None
                _tavily_iterator = None


# ---------------------------------------------------------------------------
# Provider invocation helpers
# ---------------------------------------------------------------------------

async def _try_gemini(messages: list, temperature: float) -> object:
    """Try Gemini keys in round-robin order using the google-genai SDK."""
    import asyncio
    from google import genai
    from app.core.config import get_settings

    keys = get_active_gemini_keys()
    if not keys:
        raise RuntimeError("No active Gemini keys.")

    settings = get_settings()
    last_exc: Exception | None = None

    # Convert langchain messages to plain text prompt
    prompt_parts = []
    for msg in messages:
        role = getattr(msg, "type", "") or getattr(msg, "role", "")
        content = getattr(msg, "content", str(msg))
        if role == "system":
            prompt_parts.append(f"[System]: {content}")
        else:
            prompt_parts.append(content)
    prompt = "\n\n".join(prompt_parts)

    # Try each key (start from round-robin position)
    tried_keys = set()
    for _ in range(len(keys)):
        key = _get_next_gemini_key()
        if key in tried_keys:
            continue
        tried_keys.add(key)

        try:
            client = genai.Client(api_key=key)

            def _call():
                return client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config={"temperature": temperature},
                )

            response = await asyncio.get_event_loop().run_in_executor(None, _call)

            class _Result:
                content = response.text

            return _Result()

        except Exception as exc:
            s = str(exc).lower()
            if "429" in s or "quota" in s or "resource_exhausted" in s or "exhausted" in s:
                mark_gemini_key_bad(key)
                last_exc = exc
                continue
            else:
                # For other errors (5xx, network), don't burn the key
                last_exc = exc
                continue

    raise last_exc or RuntimeError("All Gemini keys exhausted.")


async def _try_groq(messages: list, temperature: float) -> object:
    """Try Groq keys in round-robin order."""
    from langchain_groq import ChatGroq
    from app.core.config import get_settings

    keys = get_active_groq_keys()
    if not keys:
        raise RuntimeError("No active Groq keys.")

    settings = get_settings()
    last_exc: Exception | None = None

    tried_keys = set()
    for _ in range(len(keys)):
        key = _get_next_groq_key()
        if key in tried_keys:
            continue
        tried_keys.add(key)

        try:
            llm = ChatGroq(
                model=settings.groq_model,
                api_key=key,
                temperature=min(temperature, 1.0),
                max_retries=1,
            )
            return await llm.ainvoke(messages)

        except Exception as exc:
            s = str(exc).lower()
            if "429" in s or "rate_limit" in s or "quota" in s:
                mark_groq_key_bad(key)
                last_exc = exc
                continue
            raise

    raise last_exc or RuntimeError("All Groq keys exhausted.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def invoke_gemini_with_fallback(
    messages: list,
    temperature: float = 0.3,
    **_ignored,
) -> object:
    """Invoke an LLM with automatic two-tier provider fallback.

    Tries providers in order:  Gemini → Groq
    Raises only if every provider fails.
    """
    providers = [
        ("Gemini", _try_gemini),
        ("Groq",   _try_groq),
    ]

    last_exc: Exception | None = None
    for name, fn in providers:
        try:
            result = await fn(messages, temperature)
            logger.info("LLM call succeeded via %s.", name)
            return result
        except Exception as exc:
            logger.warning("%s unavailable: %s", name, exc)
            last_exc = exc

    raise last_exc or RuntimeError("All LLM providers failed.")


async def stream_with_fallback(messages: list, temperature: float = 0.3):
    """Async generator that yields tokens from the first available LLM provider.

    Tries Gemini (full response) → Groq (token streaming).
    """
    # Try Gemini first (yields full response — SDK doesn't support token streaming easily)
    try:
        result = await _try_gemini(messages, temperature)
        content = result.content if hasattr(result, 'content') else str(result)
        if content:
            yield content
            logger.info("Streaming succeeded via Gemini (full response).")
            return
    except Exception as exc:
        logger.warning("Gemini streaming failed: %s", exc)

    # Fall back to Groq streaming (true token-by-token)
    try:
        from langchain_groq import ChatGroq
        from app.core.config import get_settings
        keys = get_active_groq_keys()
        settings = get_settings()
        if keys:
            tried_keys = set()
            for _ in range(len(keys)):
                key = _get_next_groq_key()
                if key in tried_keys:
                    continue
                tried_keys.add(key)
                try:
                    llm = ChatGroq(
                        model=settings.groq_model,
                        api_key=key,
                        temperature=min(temperature, 1.0),
                        max_retries=1,
                    )
                    async for chunk in llm.astream(messages):
                        token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                        if token:
                            yield token
                    logger.info("Streaming succeeded via Groq.")
                    return
                except Exception as exc:
                    s = str(exc).lower()
                    if "429" in s or "rate_limit" in s or "quota" in s:
                        mark_groq_key_bad(key)
                        continue
                    raise
    except ImportError:
        logger.warning("langchain_groq not installed, skipping Groq streaming.")
    except Exception as exc:
        logger.warning("Groq streaming failed: %s", exc)

    raise RuntimeError("All LLM providers failed for streaming.")
