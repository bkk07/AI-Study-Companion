from pydantic import BaseModel, Field, field_validator


def _stripped(v: str) -> str:
    if not isinstance(v, str):
        raise ValueError("must be a string")
    s = v.strip()
    if not s:
        raise ValueError("must not be empty")
    return s


class ConceptOutline(BaseModel):
    """Single concept — LLM output, validated before any persistence."""

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)

    _t = field_validator("title", mode="before")(_stripped)
    _s = field_validator("summary", mode="before")(_stripped)


class SubtopicOutline(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    concepts: list[ConceptOutline] = Field(min_length=1, max_length=20)

    _t = field_validator("title", mode="before")(_stripped)


class TopicOutline(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subtopics: list[SubtopicOutline] = Field(min_length=1, max_length=10)

    _t = field_validator("title", mode="before")(_stripped)


class StructureOutline(BaseModel):
    """Validated Topic → Subtopic → Concept outline (Phase 24, no DB yet)."""

    topics: list[TopicOutline] = Field(min_length=1, max_length=10)
