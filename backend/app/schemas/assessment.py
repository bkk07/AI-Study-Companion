import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OpenEndedGradeRequest(BaseModel):
    """Grade one free-text answer — project comes from the path."""

    concept_id: uuid.UUID
    answer_text: str = Field(min_length=1, max_length=5000)
    # When the answer responds to an AI-generated question, pass it back so
    # grading stays question-aware. Omitted by legacy clients (then grading
    # uses the concept material alone, as before).
    question_text: str | None = Field(default=None, max_length=2000)

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
    strengths: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class OpenEndedGenerateRequest(BaseModel):
    """Generate one open-ended question for a scope — project comes from the path.

    Same scope contract as MCQ quiz generation (project/topic/subtopic/concept),
    plus the ``"practice"`` multi-select scope (topic_ids/subtopic_ids/concept_ids
    union) backing the Practice and Open Ended Answers pickers.
    """

    scope: str = Field(default="concept", pattern="^(project|topic|subtopic|concept|practice)$")
    topic_id: uuid.UUID | None = None
    subtopic_id: uuid.UUID | None = None
    concept_id: uuid.UUID | None = None
    topic_ids: list[uuid.UUID] | None = None
    subtopic_ids: list[uuid.UUID] | None = None
    concept_ids: list[uuid.UUID] | None = None
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


class OpenEndedGenerateResponse(BaseModel):
    """One generated question — ephemeral (no rows), graded via open-ended."""

    question_text: str
    concept_id: uuid.UUID
    scope_label: str
    difficulty: str | None = None


class ExplainBackRequest(BaseModel):
    """Explain one concept in the student's own words — project from the path."""

    concept_id: uuid.UUID
    explanation_text: str = Field(min_length=1, max_length=5000)

    @field_validator("explanation_text")
    @classmethod
    def _strip_explanation(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("explanation_text must be non-empty")
        return v


class ExplainBackResponse(BaseModel):
    """Graded explanation plus its append-only evidence id."""

    evidence_id: uuid.UUID
    concept_id: uuid.UUID
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "partial", "fail"]
    feedback: str
