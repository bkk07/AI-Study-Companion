"""Best-effort vision captioning for PDF figures (worker only).

Uses NaraRouter (OpenAI-compatible chat completions + image_url) with the
stepfun vision model. Async-first via httpx.AsyncClient; sync wrappers are
kept for the current sync extraction pipeline. Never raises: any missing
key, network error, or bad response returns None so the extraction router
falls back to cropped-OCR / placeholder text and the document still succeeds.

Disabled automatically under pytest (PYTEST_CURRENT_TEST) so unit tests never
hit the network.
"""

import asyncio
import base64
import json
import logging
import os
import re

from pydantic import BaseModel, Field, field_validator

log = logging.getLogger(__name__)

_PROMPT = (
    "Describe this figure from a study document in 2-4 sentences for a student "
    "who cannot see it. Name the figure type (diagram, chart, photo, table scan, "
    "illustration), state what it shows, and transcribe any visible labels, "
    "numbers, or key text verbatim. Plain text only, no markdown."
)

FIGURE_TYPES = ("CHART", "TABLE_SCAN", "DIAGRAM", "PHOTO", "DECORATIVE")

_ANALYZE_SYSTEM = (
    "You analyze one figure cropped from a study document. "
    "Return ONLY a JSON object with this exact shape: "
    '{"figure_type": string, "summary": string, '
    '"markdown_table": string or null, "latex_table": string or null}. '
    "figure_type must be exactly one of: CHART, TABLE_SCAN, DIAGRAM, PHOTO, DECORATIVE. "
    "CHART = bar/line/pie/scatter plot or graph (then put the read-off data values "
    "as a GitHub-Flavored Markdown table in markdown_table, latex_table null). "
    "TABLE_SCAN = a photographed/scanned data table (then put it as a LaTeX tabular "
    "in latex_table, markdown_table null). "
    "DIAGRAM, PHOTO, DECORATIVE = both table fields null. "
    "DECORATIVE = logo, border, icon, or blank patch with no study value "
    "(summary may be empty). "
    "summary: 1-4 sentences naming the type, what it shows, and any visible "
    "labels/numbers verbatim (1-800 chars; empty string only for DECORATIVE). "
    "No markdown fences, no commentary, JSON only."
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class FigureAnalysis(BaseModel):
    """Validated vision output for one figure — untrusted data until parsed."""

    figure_type: str = Field(min_length=1, max_length=16)
    summary: str = Field(default="", max_length=2000)
    markdown_table: str | None = Field(default=None, max_length=8000)
    latex_table: str | None = Field(default=None, max_length=8000)

    @field_validator("figure_type", mode="before")
    @classmethod
    def _coerce_type(cls, v) -> str:
        s = str(v or "").strip().upper()
        return s if s in FIGURE_TYPES else "DIAGRAM"

    @field_validator("summary", mode="before")
    @classmethod
    def _coerce_summary(cls, v) -> str:
        return str(v or "").strip()[:2000]

    @field_validator("markdown_table", "latex_table", mode="before")
    @classmethod
    def _coerce_table(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s[:8000] or None


def _parse_analysis_json(content: str) -> dict | None:
    """Extract a JSON object from model output (fences tolerated)."""
    text = (content or "").strip()
    if not text:
        return None
    m = _FENCE_RE.search(text)
    candidate = m.group(1).strip() if m else text
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            return None
    return parsed if isinstance(parsed, dict) else None


def _vision_config() -> tuple[str, str, float] | None:
    """(chat_url, model, timeout) or None when disabled/unconfigured."""
    try:
        from app.core.config import get_settings

        s = get_settings()
        if not getattr(s, "vision_enabled", True):
            return None
        api_key = (getattr(s, "nararouter_api_key", "") or "").strip()
        if not api_key:
            return None
        base = (getattr(s, "nararouter_base_url", "") or "").strip().rstrip("/")
        model = (
            (getattr(s, "nararouter_model", "") or "").strip()
            or (getattr(s, "vision_model", "") or "").strip()
            or "stepfun-3.7-flash"
        )
        timeout = float(getattr(s, "vision_timeout_s", 20.0) or 20.0)
        # Key stored on settings for the async call (never logged).
        _vision_config.api_key = api_key  # type: ignore[attr-defined]
        return (f"{base}/chat/completions", model, timeout)
    except Exception:
        return None


def _vision_api_key() -> str:
    key = getattr(_vision_config, "api_key", "")
    if key:
        return str(key)
    try:
        from app.core.config import get_settings

        return (get_settings().nararouter_api_key or "").strip()
    except Exception:
        return os.getenv("NARAROUTER_API_KEY", "").strip()


def is_vision_available() -> bool:
    """True when NaraRouter key exists, vision not disabled, not under pytest."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    cfg = _vision_config()
    return cfg is not None


def _build_payload(b64: str, model: str) -> dict:
    return {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 350,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }
        ],
    }


async def acaption_image_bytes(
    png_bytes: bytes,
    *,
    page_number: int = 0,
    fig_index: int = 0,
    timeout: float | None = None,
) -> str | None:
    """Async caption of one cropped figure PNG. Returns None on any failure."""
    if not png_bytes:
        return None
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    cfg = _vision_config()
    if cfg is None:
        return None
    chat_url, model, default_timeout = cfg
    api_key = _vision_api_key()
    if not api_key:
        return None
    if len(png_bytes) > 1_500_000:  # keep data-URI payloads small
        return None
    try:
        import httpx

        b64 = base64.b64encode(png_bytes).decode("ascii")
        headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=timeout or default_timeout) as client:
            resp = await client.post(
                chat_url, json=_build_payload(b64, model), headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Some providers return content blocks instead of a plain string.
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        text = (content or "").strip()
        if len(text) < 10:
            return None
        return text[:1500]
    except Exception as e:
        log.warning("vision caption failed p=%s fig=%s: %s", page_number, fig_index, str(e)[:200])
        return None


async def acaption_many(
    items: list[tuple[bytes, int, int]],
    *,
    timeout: float | None = None,
) -> list[str | None]:
    """Concurrent captions for [(png, page_number, fig_index)]. Order kept."""
    if not items:
        return []
    return list(
        await asyncio.gather(
            *(
                acaption_image_bytes(png, page_number=pn, fig_index=fi, timeout=timeout)
                for png, pn, fi in items
            )
        )
    )


def caption_image_bytes(
    png_bytes: bytes,
    *,
    page_number: int = 0,
    fig_index: int = 0,
    timeout: float | None = None,
) -> str | None:
    """Sync wrapper (extraction pipeline is sync). Runs the async call."""
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                acaption_image_bytes(
                    png_bytes, page_number=page_number, fig_index=fig_index, timeout=timeout
                )
            )
        # Inside a running loop (shouldn't happen in Celery): use a thread.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run,
                acaption_image_bytes(
                    png_bytes, page_number=page_number, fig_index=fig_index, timeout=timeout
                ),
            ).result()
    except Exception as e:
        log.warning("vision caption failed p=%s fig=%s: %s", page_number, fig_index, str(e)[:200])
        return None


async def aanalyze_figure_bytes(
    png_bytes: bytes,
    *,
    page_number: int = 0,
    fig_index: int = 0,
    timeout: float | None = None,
) -> dict | None:
    """Classify + structurally describe one figure (chart→MD, table→LaTeX).

    Returns a validated FigureAnalysis dict, or None when vision is
    unavailable/fails twice (caller falls back to caption/OCR/placeholder).
    """
    if not png_bytes:
        return None
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    cfg = _vision_config()
    if cfg is None:
        return None
    chat_url, model, default_timeout = cfg
    api_key = _vision_api_key()
    if not api_key or len(png_bytes) > 1_500_000:
        return None
    try:
        import httpx

        b64 = base64.b64encode(png_bytes).decode("ascii")
        payload = {
            "model": model,
            "temperature": 0.0,
            "max_tokens": 700,
            "messages": [
                {"role": "system", "content": _ANALYZE_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this figure. JSON only."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                },
            ],
        }
        headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=timeout or default_timeout) as client:
            for _ in range(2):  # initial + one retry
                try:
                    resp = await client.post(chat_url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    if isinstance(content, list):
                        content = " ".join(
                            b.get("text", "") for b in content if isinstance(b, dict)
                        )
                    parsed = _parse_analysis_json(str(content or ""))
                    if parsed is None:
                        last_error = ValueError("non-JSON vision output")
                        continue
                    return FigureAnalysis.model_validate(parsed).model_dump(mode="json")
                except Exception as e:
                    last_error = e
                    continue
        log.warning(
            "vision analyze failed p=%s fig=%s: %s",
            page_number,
            fig_index,
            str(last_error)[:200],
        )
        return None
    except Exception as e:
        log.warning("vision analyze failed p=%s fig=%s: %s", page_number, fig_index, str(e)[:200])
        return None


def analyze_figure_bytes(
    png_bytes: bytes,
    *,
    page_number: int = 0,
    fig_index: int = 0,
    timeout: float | None = None,
) -> dict | None:
    """Sync wrapper for aanalyze_figure_bytes (sync Celery pipeline)."""
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                aanalyze_figure_bytes(
                    png_bytes, page_number=page_number, fig_index=fig_index, timeout=timeout
                )
            )
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run,
                aanalyze_figure_bytes(
                    png_bytes, page_number=page_number, fig_index=fig_index, timeout=timeout
                ),
            ).result()
    except Exception as e:
        log.warning("vision analyze failed p=%s fig=%s: %s", page_number, fig_index, str(e)[:200])
        return None
