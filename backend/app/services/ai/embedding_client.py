"""Embeddings client — local fastembed only (no LangChain, no network API).

Uses BAAI/bge-small-en-v1.5 (384 dims) via fastembed. The model needs no API
key and no network after its one-time download; it is baked into the Docker
image. Contract: one 384-dim vector per input, in order, matching the
``embeddings.embedding Vector(384)`` column (EMBEDDING_DIMS).
"""

from functools import lru_cache

from app.models.embedding import EMBEDDING_DIMS

LOCAL_MODEL = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _local_model():  # type: ignore[no-untyped-def]
    from fastembed import TextEmbedding

    return TextEmbedding(LOCAL_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts, returning one 384-dim vector per input in order.

    Raises:
        ValueError: on empty input or unexpected model output dims.
    """
    if not texts or any(not t or not t.strip() for t in texts):
        raise ValueError("texts must be a non-empty list of non-empty strings")
    vectors = [list(map(float, vec)) for vec in _local_model().embed(texts)]
    bad = sorted({len(v) for v in vectors if len(v) != EMBEDDING_DIMS})
    if bad:
        raise ValueError(
            f"Local embedding model {LOCAL_MODEL} returned dims {bad}, "
            f"expected {EMBEDDING_DIMS}"
        )
    return vectors


def active_model_name() -> str:
    """Return the model label stored on Embedding rows."""
    return LOCAL_MODEL


def embed_one(text: str) -> list[float]:
    """Embed a single text (e.g. a retrieval query)."""
    return embed([text])[0]
