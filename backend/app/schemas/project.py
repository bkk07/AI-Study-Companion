import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    goal: str | None = Field(default=None, max_length=1000)


class ProjectRead(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    name: str
    description: str | None = None
    goal: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
