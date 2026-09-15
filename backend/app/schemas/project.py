import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectRead(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
