"""Embeddings client — local fastembed default, OpenAI fallback (no LangChain).

Provider is selected by EMBEDDING_PROVIDER (`local` default, `openai` needs
OPENAI_API_KEY). Both backends share one contract: one vector per input, in
order. The local model (BAAI/bge-small-en-v1.5, 384 dims) needs no key and no
network after its one-time download; it is baked into the Docker image.
API key is never logged.
"""

from functools import lru_cache

import httpx

from app.core.config import get_settings

OPENAI_API_URL = "https://api.openai.com/v1/embeddings"

LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
LOCAL_DIMS = 384


@lru_cache(maxsize=1)
def _local_model():  # type: ignore[no-untyped-def]
    from fastembed import TextEmbedding

    return TextEmbedding(LOCAL_MODEL)


def _embed_local(texts: list[str]) -> list[list[float]]:
    return [list(map(float, vec)) for vec in _local_model().embed(texts)]


def _embed_openai(
    texts: list[str],
    *,
    model: str | None = None,
    timeout: float = 60.0,
) -> list[list[float]]:
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


def embed(
    texts: list[str],
    *,
    model: str | None = None,
    timeout: float = 60.0,
) -> list[list[float]]:
    """Embed texts, returning one vector per input in order.

    Raises:
        ValueError: on empty input or unexpected response shape.
        RuntimeError: if provider `openai` is selected without OPENAI_API_KEY.
        httpx.HTTPError: on OpenAI transport/API errors (retryable by the caller).
    """
    if not texts or any(not t or not t.strip() for t in texts):
        raise ValueError("texts must be a non-empty list of non-empty strings")
    if get_settings().embedding_provider.strip().lower() == "openai":
        return _embed_openai(texts, model=model, timeout=timeout)
    return _embed_local(texts)


def embed_one(text: str, **kwargs) -> list[float]:
    """Embed a single text (e.g. a retrieval query)."""
    return embed([text], **kwargs)[0]
