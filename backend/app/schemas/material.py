import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialCreate(BaseModel):
    filename: str
    storage_path: str


class MaterialRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    storage_path: str
    status: str
    created_at: datetime  # uploaded_at
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
