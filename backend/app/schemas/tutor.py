import uuid

from pydantic import BaseModel, Field


class TutorAskRequest(BaseModel):
    """Tutor question — project comes from the path, never the body."""

    question: str = Field(min_length=1, max_length=2000)
    concept_id: uuid.UUID | None = None


class TutorCitation(BaseModel):
    """Chunk/material reference grounding one answer."""

    chunk_id: uuid.UUID
    material_id: uuid.UUID
    page_number: int | None = None
    source_name: str | None = None
    chunk_index: int


class TutorAskResponse(BaseModel):
    """Grounded answer or explicit unsupported response — never open memory."""

    answer: str
    supported: bool
    citations: list[TutorCitation] = Field(default_factory=list)
