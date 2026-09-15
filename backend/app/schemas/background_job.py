import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BackgroundJobRead(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    material_id: uuid.UUID | None = None
    error: str | None = None
    celery_task_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
