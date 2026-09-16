import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import get_settings
from app.services.ai import embedding_client
from app.services.ai.embedding_client import embed, embed_one


def _mock_resp(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture(autouse=True)
def _openai_provider():
    """Pin the legacy OpenAI path — local-provider tests live at the bottom."""
    os.environ["EMBEDDING_PROVIDER"] = "openai"
    get_settings.cache_clear()
    yield
    os.environ.pop("EMBEDDING_PROVIDER", None)
    get_settings.cache_clear()


def test_embed_returns_vectors_in_order():
    payload = {
        "data": [
            {"embedding": [0.2, 0.3], "index": 1},
            {"embedding": [0.1, 0.0], "index": 0},
        ]
    }
    with patch.object(embedding_client.httpx, "post", return_value=_mock_resp(payload)) as mock_post:
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["EMBEDDING_MODEL"] = "text-embedding-3-small"
        get_settings.cache_clear()
        try:
            vectors = embed(["hello", "world"])
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("EMBEDDING_MODEL", None)
            get_settings.cache_clear()
    assert vectors == [[0.1, 0.0], [0.2, 0.3]]  # reordered by index
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "text-embedding-3-small"
    assert kwargs["json"]["input"] == ["hello", "world"]
    sent_auth = mock_post.call_args[1]["headers"]["Authorization"]
    assert sent_auth == "Bearer test-key"


def test_embed_one_single_vector():
    payload = {"data": [{"embedding": [1.0, 2.0, 3.0], "index": 0}]}
    with patch.object(embedding_client.httpx, "post", return_value=_mock_resp(payload)):
        os.environ["OPENAI_API_KEY"] = "k"
        get_settings.cache_clear()
        try:
            assert embed_one("query") == [1.0, 2.0, 3.0]
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
            get_settings.cache_clear()


def test_missing_key_raises_before_http():
    with patch.object(embedding_client.httpx, "post") as mock_post:
        os.environ["OPENAI_API_KEY"] = ""
        get_settings.cache_clear()
        try:
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                embed(["hi"])
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
            get_settings.cache_clear()
    mock_post.assert_not_called()


def test_empty_input_raises():
    with pytest.raises(ValueError):
        embed([])
    with pytest.raises(ValueError):
        embed(["   "])


def test_malformed_shape_raises():
    for bad in ({"nope": []}, {"data": [{"index": 0}]}, {"data": []}):
        with patch.object(embedding_client.httpx, "post", return_value=_mock_resp(bad)):
            os.environ["OPENAI_API_KEY"] = "k"
            get_settings.cache_clear()
            try:
                with pytest.raises(ValueError):
                    embed(["hi"])
            finally:
                os.environ.pop("OPENAI_API_KEY", None)
                get_settings.cache_clear()


def test_http_error_propagates_for_retry():
    err = httpx.HTTPError("boom")
    with patch.object(embedding_client.httpx, "post", side_effect=err):
        os.environ["OPENAI_API_KEY"] = "k"
        get_settings.cache_clear()
        try:
            with pytest.raises(httpx.HTTPError):
                embed(["hi"])
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
            get_settings.cache_clear()


class TestLocalProvider:
    @pytest.fixture(autouse=True)
    def _local(self, _openai_provider):
        os.environ["EMBEDDING_PROVIDER"] = "local"
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_local_returns_384_vectors_in_order(self):
        from app.models.embedding import EMBEDDING_DIMS

        vectors = embed(["hello world", "second text"])
        assert len(vectors) == 2
        assert all(len(v) == EMBEDDING_DIMS == 384 for v in vectors)
        assert all(isinstance(x, float) for v in vectors for x in v)
        again = embed(["hello world", "second text"])
        assert again == vectors  # deterministic, no network

    def test_local_one_and_empty(self):
        assert len(embed_one("query")) == 384
        with pytest.raises(ValueError):
            embed([])
        with pytest.raises(ValueError):
            embed(["   "])
