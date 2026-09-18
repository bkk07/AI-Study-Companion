"""Local-only embeddings client tests (fastembed, no network, no API key)."""

import pytest

from app.models.embedding import EMBEDDING_DIMS
from app.services.ai.embedding_client import (
    LOCAL_MODEL,
    active_model_name,
    embed,
    embed_one,
)


def test_embed_returns_384_vectors_in_order():
    vectors = embed(["hello world", "second text"])
    assert len(vectors) == 2
    assert all(len(v) == EMBEDDING_DIMS == 384 for v in vectors)
    assert all(isinstance(x, float) for v in vectors for x in v)
    again = embed(["hello world", "second text"])
    assert again == vectors  # deterministic, no network


def test_embed_one_and_empty():
    assert len(embed_one("query")) == 384
    with pytest.raises(ValueError):
        embed([])
    with pytest.raises(ValueError):
        embed(["   "])


def test_active_model_name_is_local():
    assert active_model_name() == LOCAL_MODEL == "BAAI/bge-small-en-v1.5"
