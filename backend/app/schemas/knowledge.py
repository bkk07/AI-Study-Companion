import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CoverageRead(BaseModel):
    """Mastery + coverage pair — mastery None renders as "Not started"."""

    mastery: float | None = None
    practiced: int = 0
    total: int = 0


class BrowseConceptRead(BaseModel):
    """CORE practice target leaf for Browse-by-Topic."""

    id: uuid.UUID
    title: str
    lo_type: str
    mastery: float | None = None
    status: str
    practiced: bool = False


class BrowseSubtopicRead(BaseModel):
    id: uuid.UUID
    title: str
    core_count: int = 0
    coverage: CoverageRead = Field(default_factory=CoverageRead)
    concepts: list[BrowseConceptRead] = Field(default_factory=list)


class BrowseTopicRead(BaseModel):
    id: uuid.UUID
    title: str
    core_count: int = 0
    coverage: CoverageRead = Field(default_factory=CoverageRead)
    subtopics: list[BrowseSubtopicRead] = Field(default_factory=list)


class KnowledgeTreeRead(BaseModel):
    """Browse hierarchy — CORE mastery targets only, never the full keyword set."""

    topics: list[BrowseTopicRead] = Field(default_factory=list)
    overall: CoverageRead = Field(default_factory=CoverageRead)


class SearchHitRead(BaseModel):
    """One search hit across ALL importances (knowledge model)."""

    id: uuid.UUID
    title: str
    summary: str
    lo_type: str
    importance: str
    topic: str
    subtopic: str
    page_start: int | None = None
    page_end: int | None = None
    mastery: float | None = None
    status: str | None = None
    practicable: bool = False


class SearchResultsRead(BaseModel):
    query: str
    hits: list[SearchHitRead] = Field(default_factory=list)


class GraphNodeRead(BaseModel):
    """One CORE concept node with live mastery for the mini-map."""

    id: uuid.UUID
    title: str
    topic: str
    mastery: float | None = None
    status: str


class GraphEdgeRead(BaseModel):
    """One semantic edge between project concepts (prerequisites + related)."""

    from_id: uuid.UUID
    to_id: uuid.UUID
    relation: str


class KnowledgeGraphRead(BaseModel):
    """Project mini-map: mastery-colored nodes, prerequisite/related edges."""

    nodes: list[GraphNodeRead] = Field(default_factory=list)
    edges: list[GraphEdgeRead] = Field(default_factory=list)


class StreamRead(BaseModel):
    value: float | None = None
    count: int = 0


class ConceptDetailRead(BaseModel):
    """Concept-detail aggregate — composed reads, technical metadata hidden."""

    id: uuid.UUID
    title: str
    summary: str
    lo_type: str
    importance: str
    mastery: float | None = None
    status: str
    mcq: StreamRead = Field(default_factory=StreamRead)
    applied: StreamRead = Field(default_factory=StreamRead)
    # Plan A: weighted final + per-stream breakdown (additive).
    final_mastery: float | None = None
    evidence_confidence: str = "none"
    streams: dict[str, StreamRead] = Field(default_factory=dict)
    questions_attempted: int = 0
    questions_correct: int = 0
    last_practiced_at: datetime | None = None
    prerequisites: list[SearchHitRead] = Field(default_factory=list)
    related: list[SearchHitRead] = Field(default_factory=list)
    supporting: list[SearchHitRead] = Field(default_factory=list)
    source_material: str | None = None
    page_start: int | None = None
    page_end: int | None = None
