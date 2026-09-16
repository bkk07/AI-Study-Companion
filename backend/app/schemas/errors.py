from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Single machine-readable error body. `code` is stable for clients;
    `message` is human-readable and safe to display; `details` carries
    structured context (e.g. per-field validation failures)."""

    code: str
    message: str
    details: Any | None = None


class ErrorEnvelope(BaseModel):
    """The only error payload this API emits (Phase 48 guard: routes must
    not invent incompatible shapes — normalization happens in handlers)."""

    error: ErrorDetail
