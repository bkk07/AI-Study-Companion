import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Input for registration — password kept separate from read schema."""

    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    """Public user shape — no hashed_password / password."""

    id: uuid.UUID
    email: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
