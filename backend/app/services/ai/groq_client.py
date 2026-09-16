"""LLM chat client — JSON mode via httpx (no extra SDK).

Historically Groq-only (hence the module name); now provider-aware via
Settings.llm_provider ("groq" | "inception"). All callers use chat_json,
so swapping providers needs no service changes.
Sends only the required text + explicit schema instructions. LLM output is
untrusted data; callers must validate with Pydantic before persistence.
API key is never logged.
"""

import json
import re
import unicodedata

import httpx

from app.core.config import get_settings

# Per-provider wiring. min_temperature matters: Mercury 2.5 rejects anything
# below 0.5 (silently resets to 1.0), which would make quiz/map JSON
# nondeterministic — so temperature is clamped up, never down.
_PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_attr": "groq_api_key",
        "key_env": "GROQ_API_KEY",
        "model_attr": "groq_model",
        "min_temperature": 0.0,
    },
    "inception": {
        "url": "https://api.inceptionlabs.ai/v1/chat/completions",
        "key_attr": "inception_api_key",
        "key_env": "INCEPTION_API_KEY",
        "model_attr": "inception_model",
        "min_temperature": 0.5,
    },
}

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
    """Call the configured provider's chat completions in JSON mode.

    Raises:
        RuntimeError: if the active provider's API key is missing.
        ValueError: if provider unknown, or response is not a valid JSON object.
        httpx.HTTPError: on transport/API errors (retryable by caller).
    """
    settings = get_settings()
    provider_name = str(settings.llm_provider or "groq").strip().lower()
    try:
        provider = _PROVIDERS[provider_name]
    except KeyError:
        raise ValueError(
            f"Unknown LLM_PROVIDER {provider_name!r} "
            f"(expected one of {sorted(_PROVIDERS)})"
        ) from None
    api_key = getattr(settings, provider["key_attr"])
    if not api_key:
        raise RuntimeError(f"{provider['key_env']} is not configured")
    system, user = sanitize_for_llm(system), sanitize_for_llm(user)
    resolved_model = model or getattr(settings, provider["model_attr"])
    resolved_temp = max(temperature, provider["min_temperature"])
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": resolved_model,
        "temperature": resolved_temp,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    resp = httpx.post(provider["url"], json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Unexpected {provider_name} response shape: {e}") from e
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"{provider_name} response was not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError(f"{provider_name} response JSON must be an object")
    return parsed
