"""Groq chat client — JSON mode via httpx (no extra SDK).

Sends only the required text + explicit schema instructions. LLM output is
untrusted data; callers must validate with Pydantic before persistence.
API key is never logged.
"""

import json
import re
import unicodedata

import httpx

from app.core.config import get_settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# PDF extraction leaves junk that derails constrained JSON generation
# (observed: U+FFFD replacement chars → Groq `json_validate_failed` 400s).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def sanitize_for_llm(text: str) -> str:
    """Make extracted text safe for LLM prompts without changing its meaning.

    NFKC folds ligatures/compatibility forms, replacement chars (evidence of
    undecodable bytes, never real content) become spaces, and control codes
    that have no business in JSON prompts are dropped. Newlines/tabs kept.
    """
    if not text:
        return text
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\ufffd", " ")
    return _CONTROL_RE.sub("", cleaned)


def chat_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    timeout: float = 60.0,
) -> dict:
    """Call Groq chat completions in JSON mode, return parsed JSON dict.

    Raises:
        RuntimeError: if GROQ_API_KEY is missing.
        ValueError: if response is not valid JSON object.
        httpx.HTTPError: on transport/API errors (retryable by caller).
    """
    settings = get_settings()
    api_key = settings.groq_api_key
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    system, user = sanitize_for_llm(system), sanitize_for_llm(user)
    resolved_model = model or settings.groq_model
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": resolved_model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    resp = httpx.post(GROQ_API_URL, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Unexpected Groq response shape: {e}") from e
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Groq response was not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError("Groq response JSON must be an object")
    return parsed
