from pydantic import BaseModel, Field, field_validator


class MCQQuestionOutline(BaseModel):
    """One proposed MCQ — validated before any persistence (Phase 35)."""

    question_text: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)
    difficulty: str = Field(pattern="^(easy|medium|hard)$")

    @field_validator("question_text")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question_text must be non-empty")
        return v

    @field_validator("options")
    @classmethod
    def _strip_options(cls, v: list[str]) -> list[str]:
        cleaned = [o.strip() for o in v]
        if any(not o for o in cleaned):
            raise ValueError("options must all be non-empty strings")
        return cleaned


class MCQOutline(BaseModel):
    """Model-proposed question set — correct_index range checked by service."""

    questions: list[MCQQuestionOutline] = Field(min_length=1, max_length=20)
