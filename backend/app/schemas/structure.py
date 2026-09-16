from pydantic import BaseModel, Field, field_validator

from app.models.concept import LO_IMPORTANCES, LO_TYPES
from app.models.concept_relationship import RELATIONS


def _stripped(v: str) -> str:
    if not isinstance(v, str):
        raise ValueError("must be a string")
    s = v.strip()
    if not s:
        raise ValueError("must not be empty")
    return s


def _lo_type(v: str) -> str:
    s = _stripped(v).upper()
    if s not in LO_TYPES:
        raise ValueError(f"type must be one of {list(LO_TYPES)}")
    return s


def _importance(v: str) -> str:
    s = _stripped(v).upper()
    if s not in LO_IMPORTANCES:
        raise ValueError(f"importance must be one of {list(LO_IMPORTANCES)}")
    return s


def _relation(v: str) -> str:
    s = _stripped(v).upper()
    if s not in RELATIONS:
        raise ValueError(f"relation must be one of {list(RELATIONS)}")
    return s


def _optional_section(v) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("must be a string or null")
    return v.strip() or None


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


# --- Extraction v2 (Phase B): two-pass learning-object pipeline -------------


class SubtopicSpanOutline(BaseModel):
    """One subtopic with its page span inside the parent topic's span."""

    title: str = Field(min_length=1, max_length=200)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)

    _t = field_validator("title", mode="before")(_stripped)


class TopicSpanOutline(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    subtopics: list[SubtopicSpanOutline] = Field(min_length=1, max_length=12)

    _t = field_validator("title", mode="before")(_stripped)


class TopicMapOutline(BaseModel):
    """Pass-1 output: topics/subtopics with page spans (no learning objects yet)."""

    topics: list[TopicSpanOutline] = Field(min_length=1, max_length=20)


class RelationshipProposal(BaseModel):
    """One LLM-proposed semantic edge to a sibling object named `to_name`.

    Resolved to ids at persist time; unresolvable names are dropped.
    evidence_span is mandatory here AND at the DB CHECK — no evidence, no edge.
    """

    to_name: str = Field(min_length=1, max_length=200)
    relation: str = Field(min_length=1, max_length=32)
    evidence_span: str = Field(min_length=1, max_length=1000)

    _n = field_validator("to_name", mode="before")(_stripped)
    _r = field_validator("relation", mode="before")(_relation)
    _e = field_validator("evidence_span", mode="before")(_stripped)


class LearningObjectOutline(BaseModel):
    """Pass-2 output: one classified learning object with provenance."""

    name: str = Field(min_length=1, max_length=200)
    subtopic: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=32)
    importance: str = Field(min_length=1, max_length=16)
    summary: str = Field(min_length=1, max_length=1000)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section: str | None = Field(default=None, max_length=300)
    relationships: list[RelationshipProposal] = Field(default_factory=list, max_length=5)

    _n = field_validator("name", mode="before")(_stripped)
    _s = field_validator("subtopic", mode="before")(_stripped)
    _t = field_validator("type", mode="before")(_lo_type)
    _i = field_validator("importance", mode="before")(_importance)
    _sum = field_validator("summary", mode="before")(_stripped)
    _sec = field_validator("section", mode="before")(_optional_section)


class TopicLearningObjects(BaseModel):
    """Pass-2 output for one topic: its learning objects (may be empty)."""

    objects: list[LearningObjectOutline] = Field(default_factory=list, max_length=60)
