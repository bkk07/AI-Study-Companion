import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialCreate(BaseModel):
    filename: str
    storage_path: str


class EnrichmentStatus(BaseModel):
    """Per-stage pipeline progress for one material (list endpoint only).

    - `extraction`: the material's own DB status (pending/processing/ready/failed).
    - `embeddings` / `structure`: latest downstream job status, or None when
      that stage was never queued (e.g. extraction still running or failed).
    The UI uses this to show "Ready — building learning map…" instead of
    one opaque spinner: extracted text is readable as soon as `extraction`
    is ready, even while enrichment stages are still active.
    """

    extraction: str
    embeddings: str | None = None
    structure: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MaterialRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    storage_path: str
    status: str
    page_count: int | None = None
    error_message: str | None = None
    created_at: datetime  # uploaded_at
    updated_at: datetime
    enrichment: EnrichmentStatus | None = None

    model_config = ConfigDict(from_attributes=True)
