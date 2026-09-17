"""LLM chat client — JSON mode via httpx (no extra SDK).

Historically Groq-only (hence the module name); now provider-aware via
Settings.llm_provider ("groq" | "inception"). All callers use chat_json,
so swapping providers needs no service changes.
Sends only the required text + explicit schema instructions. LLM output is
untrusted data; callers must validate with Pydantic before persistence.
API key is never logged.
"""

import contextvars
import json
import re
import time
import unicodedata
from dataclasses import dataclass

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

# Rough token fallback when a provider omits the usage block (chars/token).
_CHARS_PER_TOKEN = 4


@dataclass
class LLMCallRecord:
    """Metering for one provider call — no prompt/response text, ever."""

    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    tokens_estimated: bool = False
    latency_ms: int | None = None
    success: bool = True
    error_type: str | None = None
    # HTTP status when the failure came from the provider (400/429/5xx...).
    http_status: int | None = None


# Active metering scope: None outside app.services.ai_usage_service.track_llm_call.
# chat_json appends one record per HTTP attempt (success or failure); the
# tracker drains the list on exit. Context-local, so request threads and
# Celery worker processes never see each other's calls.
_calls_in_scope: contextvars.ContextVar[list[LLMCallRecord] | None] = (
    contextvars.ContextVar("llm_calls_in_scope", default=None)
)


def _note_call(record: LLMCallRecord) -> None:
    calls = _calls_in_scope.get()
    if calls is not None:
        calls.append(record)


def _estimate_tokens(*texts: str) -> int:
    return max(1, sum(len(t or "") for t in texts) // _CHARS_PER_TOKEN)


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

    Every HTTP attempt appends an LLMCallRecord to the active metering
    scope (if any) — see app.services.ai_usage_service.track_llm_call.
    Prompt/response text is never recorded.

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
    resp = None
    data: dict = {}
    content = ""
    start = time.perf_counter()
    try:
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
    except Exception as e:
        response = getattr(e, "response", None)
        status = getattr(response, "status_code", None)
        _note_call(
            LLMCallRecord(
                provider=provider_name,
                model=resolved_model,
                latency_ms=int((time.perf_counter() - start) * 1000),
                success=False,
                error_type=type(e).__name__,
                http_status=status if isinstance(status, int) else None,
            )
        )
        raise
    latency_ms = int((time.perf_counter() - start) * 1000)
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    # OpenAI-compatible providers disagree on key names (Inception Labs has
    # served both prompt_tokens and input_tokens shapes) — accept aliases so
    # real Mercury token counts (often millions) are recorded, not estimated.
    prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    # bool is an int subclass — exclude it so True/False never become counts.
    if (
        not isinstance(prompt_tokens, int)
        or isinstance(prompt_tokens, bool)
        or not isinstance(completion_tokens, int)
        or isinstance(completion_tokens, bool)
    ):
        # Provider omitted usage — fall back to len/4 so cost stays
        # attributable, flagged for honesty.
        prompt_tokens = _estimate_tokens(system, user)
        completion_tokens = _estimate_tokens(content)
        estimated = True
    else:
        estimated = False
    _note_call(
        LLMCallRecord(
            provider=provider_name,
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_estimated=estimated,
            latency_ms=latency_ms,
            success=True,
        )
    )
    return parsed
