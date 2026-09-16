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
        settings.return_value.llm_provider = "groq"
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        assert chat_json("SYSﬁ", "candidates�\x00answer") == {"ok": True}

    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["temperature"] == 0.0  # groq allows true zero

    user_msg = captured["json"]["messages"][1]["content"]
    assert user_msg == "candidates answer"
    assert captured["json"]["messages"][0]["content"] == "SYSfi"


def test_chat_json_missing_key_fails_fast():
    with patch("app.services.ai.groq_client.get_settings") as settings:
        settings.return_value.llm_provider = "groq"
        settings.return_value.groq_api_key = ""
        try:
            chat_json("s", "u")
        except RuntimeError as e:
            assert "GROQ_API_KEY" in str(e)
        else:
            raise AssertionError("expected RuntimeError")


def test_chat_json_missing_inception_key_names_its_env():
    with patch("app.services.ai.groq_client.get_settings") as settings:
        settings.return_value.llm_provider = "inception"
        settings.return_value.inception_api_key = ""
        try:
            chat_json("s", "u")
        except RuntimeError as e:
            assert "INCEPTION_API_KEY" in str(e)
        else:
            raise AssertionError("expected RuntimeError")


def test_chat_json_unknown_provider_rejected():
    with patch("app.services.ai.groq_client.get_settings") as settings:
        settings.return_value.llm_provider = "skynet"
        try:
            chat_json("s", "u")
        except ValueError as e:
            assert "LLM_PROVIDER" in str(e)
        else:
            raise AssertionError("expected ValueError")


def test_chat_json_inception_url_model_and_temp_clamp():
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured.update(json=json)
        captured["auth"] = headers["Authorization"]
        return FakeResp()

    with (
        patch("app.services.ai.groq_client.httpx.post", side_effect=fake_post),
        patch("app.services.ai.groq_client.get_settings") as settings,
    ):
        settings.return_value.llm_provider = " Inception "  # casing/space tolerated
        settings.return_value.inception_api_key = "test-inception-key"
        settings.return_value.inception_model = "mercury-2.5"
        assert chat_json("s", "u") == {"ok": True}

    assert captured["url"] == "https://api.inceptionlabs.ai/v1/chat/completions"
    assert captured["json"]["model"] == "mercury-2.5"
    # Mercury rejects < 0.5 (resets to 1.0) — client clamps our temp-0 default up.
    assert captured["json"]["temperature"] == 0.5
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["auth"] == "Bearer test-inception-key"


def test_chat_json_explicit_model_override_wins():
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}

    def fake_post(url, json, headers, timeout):
        captured.update(json=json)
        return FakeResp()

    with (
        patch("app.services.ai.groq_client.httpx.post", side_effect=fake_post),
        patch("app.services.ai.groq_client.get_settings") as settings,
    ):
        settings.return_value.llm_provider = "inception"
        settings.return_value.inception_api_key = "k"
        settings.return_value.inception_model = "mercury-2.5"
        chat_json("s", "u", model="mercury-2", temperature=0.9)

    assert captured["json"]["model"] == "mercury-2"
    assert captured["json"]["temperature"] == 0.9  # already above floor, untouched


def test_chat_json_transport_errors_propagate_untouched():
    with (
        patch("app.services.ai.groq_client.httpx.post",
              side_effect=httpx.ConnectError("down")),
        patch("app.services.ai.groq_client.get_settings") as settings,
    ):
        settings.return_value.llm_provider = "groq"
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        try:
            chat_json("s", "u")
        except httpx.ConnectError:
            pass
        else:
            raise AssertionError("expected ConnectError")
