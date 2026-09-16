"""Centralized error handling (Phase 48).

Every failure leaves the API as one JSON envelope:
    {"error": {"code": "<stable-machine-code>", "message": "<safe-to-display>", "details": ...}}

Routes keep raising plain `HTTPException` with domain messages; normalization
happens here at the boundary so no route can invent an incompatible payload.
Status codes are unchanged — only the body shape is unified.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

INTERNAL_ERROR_MESSAGE = "Internal server error"

# Stable machine-readable codes per status. 429 has no producer yet — the
# mapping exists so Phase 49's limiter automatically emits the envelope.
STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "authentication_required",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_unavailable",
    503: "upstream_unavailable",
}


def error_code_for_status(status_code: int) -> str:
    """Stable code for a status; 5xx default to internal/upstream buckets."""
    if status_code in STATUS_CODES:
        return STATUS_CODES[status_code]
    if 400 <= status_code < 500:
        return "bad_request"
    if status_code in (502, 503, 504):
        return "upstream_unavailable"
    return "internal_error"


def build_envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = jsonable_encoder(details)
    return body


def _safe_message(status_code: int, detail: Any) -> str:
    """Route domain messages (str, 4xx/502) pass through — they are fixed,
    user-facing strings by construction. Anything else (500s, non-str
    details that may embed tracebacks/SQL) is replaced with a generic
    message so internals never leak."""
    if isinstance(detail, str) and (status_code < 500 or status_code in (502, 503)):
        return detail
    if status_code == 422:
        return "Request validation failed"
    return INTERNAL_ERROR_MESSAGE


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = error_code_for_status(exc.status_code)
    if code == "internal_error":
        log.exception("Unhandled HTTP %s on %s %s", exc.status_code, request.method, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(code, _safe_message(exc.status_code, exc.detail)),
        headers=dict(exc.headers or {}),
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=build_envelope("validation_error", "Request validation failed", details),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=build_envelope("internal_error", INTERNAL_ERROR_MESSAGE),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_exception_handler)
