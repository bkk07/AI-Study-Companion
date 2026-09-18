import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FigureRead(BaseModel):
    """One stored figure — metadata + text twin (image bytes via image route)."""

    id: uuid.UUID
    material_id: uuid.UUID
    page_number: int
    fig_index: int
    figure_type: str = "DIAGRAM"
    summary: str | None = None
    markdown_table: str | None = None
    latex_table: str | None = None
    image_url: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class FigureListResponse(BaseModel):
    """Figures for one material, page-ordered."""

    material_id: uuid.UUID
    figures: list[FigureRead] = Field(default_factory=list)
