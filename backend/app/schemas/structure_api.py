import uuid

from pydantic import BaseModel, ConfigDict


class ConceptRead(BaseModel):
    """Public concept shape — title + summary only, no internals."""

    id: uuid.UUID
    title: str
    summary: str

    model_config = ConfigDict(from_attributes=True)


class SubtopicRead(BaseModel):
    id: uuid.UUID
    title: str
    concepts: list[ConceptRead] = []

    model_config = ConfigDict(from_attributes=True)


class TopicRead(BaseModel):
    id: uuid.UUID
    title: str
    subtopics: list[SubtopicRead] = []

    model_config = ConfigDict(from_attributes=True)


class StructureRead(BaseModel):
    """Project learning map — nested tree, project-scoped, no storage paths or prompts."""

    topics: list[TopicRead] = []
