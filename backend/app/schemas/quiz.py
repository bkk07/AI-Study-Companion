import uuid

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


class QuizGenerateRequest(BaseModel):
    """Generate a quiz for one concept — project comes from the path."""

    concept_id: uuid.UUID
    num_questions: int = Field(default=5, ge=1, le=20)
    mode: str = Field(default="practice", pattern="^(practice|exam)$")
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")


class QuizGenerateResponse(BaseModel):
    quiz_id: uuid.UUID
    question_count: int


class QuestionRead(BaseModel):
    """Question as served to the taker — never includes correct_index."""

    id: uuid.UUID
    question_text: str
    options: list[str]
    difficulty: str
    concept_id: uuid.UUID


class AttemptStartResponse(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    questions: list[QuestionRead]


class AnswerSubmitRequest(BaseModel):
    question_id: uuid.UUID
    selected_index: int = Field(ge=0)
    confidence: int | None = Field(default=None, ge=1, le=5)


class AnswerSubmitResponse(BaseModel):
    is_correct: bool
    correct_index: int
    answered_count: int
    correct_count: int


class AttemptCompleteResponse(BaseModel):
    attempt_id: uuid.UUID
    score: float | None
    correct_count: int
    total: int
