import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TutorAskRequest(BaseModel):
    """Tutor question — project comes from the path, never the body."""

    question: str = Field(min_length=1, max_length=2000)
    concept_id: uuid.UUID | None = None


class TutorCitation(BaseModel):
    """Chunk/material reference grounding one answer."""

    chunk_id: uuid.UUID
    material_id: uuid.UUID
    page_number: int | None = None
    source_name: str | None = None
    chunk_index: int
    # Short quote of the source chunk so clients can render
    # "doc.pdf · Page N · “…excerpt…”" cards. May be None for legacy rows.
    excerpt: str | None = None
    # Figure on the cited page, when one exists — lets clients render
    # "Fig Y · type · thumbnail" cards linking to the image route.
    figure_id: uuid.UUID | None = None
    figure_index: int | None = None
    figure_type: str | None = None
    image_url: str | None = None


class TutorAskResponse(BaseModel):
    """Grounded answer or explicit unsupported response — never open memory."""

    answer: str
    supported: bool
    citations: list[TutorCitation] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    """Start a chat thread — title optional, auto-set from the first question."""

    title: str | None = Field(default=None, max_length=200)


class ConversationRead(BaseModel):
    """Chat thread in list views."""

    id: uuid.UUID
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class TutorMessageRead(BaseModel):
    """One stored utterance — assistant rows carry grounding metadata."""

    id: uuid.UUID
    role: str
    content: str
    supported: bool | None = None
    citations: list[TutorCitation] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    created_at: datetime


class ConversationDetail(BaseModel):
    """Full thread with ordered messages."""

    id: uuid.UUID
    title: str
    messages: list[TutorMessageRead] = Field(default_factory=list)


class ChatSendRequest(BaseModel):
    """Ask inside a conversation — project comes from the path."""

    question: str = Field(min_length=1, max_length=2000)
    concept_id: uuid.UUID | None = None


class ChatSendResponse(BaseModel):
    """Persisted exchange: ids plus the grounded answer payload."""

    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    answer: str
    supported: bool
    citations: list[TutorCitation] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


class QuizPlanRequest(BaseModel):
    """Recent prompts to map onto quiz concepts — project comes from the path."""

    questions: list[str] = Field(min_length=1, max_length=5)

    @field_validator("questions")
    @classmethod
    def _strip_questions(cls, v: list[str]) -> list[str]:
        cleaned = [q.strip() for q in v if isinstance(q, str) and q.strip()]
        if not cleaned:
            raise ValueError("questions must contain at least one non-empty question")
        for q in cleaned:
            if len(q) > 2000:
                raise ValueError("each question must be at most 2000 characters")
        return cleaned


class QuizPlanResponse(BaseModel):
    """Concept mapping behind the quiz confirm UI (empty = no match)."""

    label: str = ""
    concept_ids: list[uuid.UUID] = Field(default_factory=list)
