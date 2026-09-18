import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


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
    """Generate a quiz scoped to project/topic/subtopic/concept/practice — project from path.

    Backward compatible: legacy clients send only ``concept_id`` (scope
    defaults to ``"concept"``). New clients send ``scope`` plus the matching
    id (``topic_id`` / ``subtopic_id`` / ``concept_id``; nothing extra for
    ``"project"``). The ``"practice"`` scope carries an explicit multi-select
    (``topic_ids`` / ``subtopic_ids`` / ``concept_ids`` union) from the
    Practice picker — selecting a topic implies all of its subtopics/concepts.
    """

    concept_id: uuid.UUID | None = None
    scope: str = Field(default="concept", pattern="^(project|topic|subtopic|concept|practice)$")
    topic_id: uuid.UUID | None = None
    subtopic_id: uuid.UUID | None = None
    topic_ids: list[uuid.UUID] | None = None
    subtopic_ids: list[uuid.UUID] | None = None
    concept_ids: list[uuid.UUID] | None = None
    num_questions: int = Field(default=5, ge=1, le=20)
    mode: str = Field(default="practice", pattern="^(practice|exam)$")
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")

    @model_validator(mode="after")
    def _check_scope_ids(self):
        if self.scope == "concept" and self.concept_id is None:
            raise ValueError("concept_id is required when scope is 'concept'")
        if self.scope == "topic" and self.topic_id is None:
            raise ValueError("topic_id is required when scope is 'topic'")
        if self.scope == "subtopic" and self.subtopic_id is None:
            raise ValueError("subtopic_id is required when scope is 'subtopic'")
        if self.scope == "practice" and not any([self.topic_ids, self.subtopic_ids, self.concept_ids]):
            raise ValueError(
                "at least one of topic_ids, subtopic_ids, concept_ids is required when scope is 'practice'"
            )
        return self


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
    # Answer-time adaptation: the deterministically selected next unanswered
    # question in this quiz (None when nothing remains). Additive — legacy
    # clients ignore it and keep stepping through their question list.
    next_question: QuestionRead | None = None


class AttemptCompleteResponse(BaseModel):
    attempt_id: uuid.UUID
    score: float | None
    correct_count: int
    total: int
