"""OpenAI embeddings client — thin httpx wrapper, no LangChain.

Isolates the embeddings dependency behind a mockable interface for the
Phase 29 worker. Embeddings are separate from Groq generation; this module
never calls the tutor model. API key is never logged.
"""

import httpx

from app.core.config import get_settings

OPENAI_API_URL = "https://api.openai.com/v1/embeddings"


def embed(
    texts: list[str],
    *,
    model: str | None = None,
    timeout: float = 60.0,
) -> list[list[float]]:
    """Embed texts, returning one vector per input in order.

    Raises:
        RuntimeError: if OPENAI_API_KEY is missing.
        ValueError: on empty input or unexpected response shape.
        httpx.HTTPError: on transport/API errors (retryable by the caller).
    """
    if not texts or any(not t or not t.strip() for t in texts):
        raise ValueError("texts must be a non-empty list of non-empty strings")
    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {"model": model or settings.embedding_model, "input": texts}
    resp = httpx.post(OPENAI_API_URL, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    try:
        items = data["data"]
        ordered = sorted(items, key=lambda d: d["index"])
        vectors = [list(map(float, d["embedding"])) for d in ordered]
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ValueError(f"Unexpected embeddings response shape: {e}") from e
    if len(vectors) != len(texts) or any(not v for v in vectors):
        raise ValueError("Embeddings response did not cover all inputs")
    return vectors


def embed_one(text: str, **kwargs) -> list[float]:
    """Embed a single text (e.g. a retrieval query in Phase 30)."""
    return embed([text], **kwargs)[0]
