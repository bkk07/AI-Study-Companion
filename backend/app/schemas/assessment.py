import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OpenEndedGradeRequest(BaseModel):
    """Grade one free-text answer — project comes from the path."""

    concept_id: uuid.UUID
    answer_text: str = Field(min_length=1, max_length=5000)

    @field_validator("answer_text")
    @classmethod
    def _strip_answer(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("answer_text must be non-empty")
        return v


class OpenEndedGradeResponse(BaseModel):
    """Structured grade — verdict is a deterministic band over score."""

    concept_id: uuid.UUID
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "partial", "fail"]
    feedback: str
