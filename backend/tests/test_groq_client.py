"""Groq client: prompt sanitization (real unit tests, HTTP mocked)."""

from unittest.mock import patch

import httpx

from app.services.ai.groq_client import chat_json, sanitize_for_llm


def test_sanitize_replaces_replacement_chars_and_folds_forms():
    assert sanitize_for_llm("candidates�ability") == "candidates ability"
    assert sanitize_for_llm("ﬁle") == "file"  # fi ligature folded
    assert sanitize_for_llm("plain text") == "plain text"
    assert sanitize_for_llm("") == ""


def test_sanitize_strips_controls_keeps_structure():
    assert sanitize_for_llm("a\x00b\x07c\x1bd") == "abcd"
    assert sanitize_for_llm("line1\nline2\ttab") == "line1\nline2\ttab"
    assert sanitize_for_llm("a\x7fb\x9fc") == "abc"


def test_chat_json_sends_sanitized_prompts():
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    def fake_post(url, json, headers, timeout):
        captured.update(json=json)
        return FakeResp()

    with (
        patch("app.services.ai.groq_client.httpx.post", side_effect=fake_post),
        patch("app.services.ai.groq_client.get_settings") as settings,
    ):
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        assert chat_json("SYSﬁ", "candidates�\x00answer") == {"ok": True}

    user_msg = captured["json"]["messages"][1]["content"]
    assert user_msg == "candidates answer"
    assert captured["json"]["messages"][0]["content"] == "SYSfi"


def test_chat_json_missing_key_fails_fast():
    with patch("app.services.ai.groq_client.get_settings") as settings:
        settings.return_value.groq_api_key = ""
        try:
            chat_json("s", "u")
        except RuntimeError as e:
            assert "GROQ_API_KEY" in str(e)
        else:
            raise AssertionError("expected RuntimeError")


def test_chat_json_transport_errors_propagate_untouched():
    with (
        patch("app.services.ai.groq_client.httpx.post",
              side_effect=httpx.ConnectError("down")),
        patch("app.services.ai.groq_client.get_settings") as settings,
    ):
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        try:
            chat_json("s", "u")
        except httpx.ConnectError:
            pass
        else:
            raise AssertionError("expected ConnectError")
