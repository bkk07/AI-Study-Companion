"""Groq chat client — JSON mode via httpx (no extra SDK).

Sends only the required text + explicit schema instructions. LLM output is
untrusted data; callers must validate with Pydantic before persistence.
API key is never logged.
"""

import json

import httpx

from app.core.config import get_settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


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
