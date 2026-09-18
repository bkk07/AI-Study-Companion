import uuid

from pydantic import BaseModel, Field


class RagChunk(BaseModel):
    """One context item — chunk text plus citation metadata for consumers."""

    chunk_id: uuid.UUID
    material_id: uuid.UUID
    content: str
    page_number: int | None = None
    source_name: str | None = None
    chunk_index: int
    score: float


class RagFigure(BaseModel):
    """Figure linked to retrieved pages — citation-grade, image via URL."""

    figure_id: uuid.UUID
    material_id: uuid.UUID
    page_number: int
    fig_index: int
    figure_type: str = "DIAGRAM"
    summary: str | None = None
    image_url: str | None = None


class RagContext(BaseModel):
    """Bounded retrieval context — consumer-neutral, no tutor/quiz wording."""

    query: str
    scope_project_id: uuid.UUID
    scope_concept_id: uuid.UUID | None = None
    chunks: list[RagChunk] = Field(default_factory=list)
    figures: list[RagFigure] = Field(default_factory=list)
    total_chars: int = 0
    truncated: bool = False
