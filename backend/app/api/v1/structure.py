from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import get_authorized_project
from app.models.concept import Concept
from app.models.project import Project
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.schemas.structure_api import ConceptRead, StructureRead, SubtopicRead, TopicRead

router = APIRouter(prefix="/projects/{project_id}/structure", tags=["structure"])


@router.get("", response_model=StructureRead)
def get_structure(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
) -> StructureRead:
    """Return the project's learning map as a stable nested tree.

    Project-scoped: only rows with matching project_id are read. Response
    contains titles/summaries only — never storage paths or AI prompts.
    """
    topics = (
        db.query(Topic)
        .filter(Topic.project_id == project.id)
        .order_by(Topic.created_at.asc())
        .all()
    )
    if not topics:
        return StructureRead(topics=[])

    topic_ids = [t.id for t in topics]
    subtopics = (
        db.query(Subtopic)
        .filter(Subtopic.project_id == project.id, Subtopic.topic_id.in_(topic_ids))
        .order_by(Subtopic.created_at.asc())
        .all()
    )
    sub_by_topic: dict[str, list[Subtopic]] = {}
    for s in subtopics:
        sub_by_topic.setdefault(str(s.topic_id), []).append(s)

    sub_ids = [s.id for s in subtopics]
    concepts: list[Concept] = []
    if sub_ids:
        concepts = (
            db.query(Concept)
            .filter(Concept.project_id == project.id, Concept.subtopic_id.in_(sub_ids))
            .order_by(Concept.created_at.asc())
            .all()
        )
    con_by_sub: dict[str, list[Concept]] = {}
    for c in concepts:
        con_by_sub.setdefault(str(c.subtopic_id), []).append(c)

    return StructureRead(
        topics=[
            TopicRead(
                id=t.id,
                title=t.title,
                subtopics=[
                    SubtopicRead(
                        id=s.id,
                        title=s.title,
                        concepts=[
                            ConceptRead(id=c.id, title=c.title, summary=c.summary)
                            for c in con_by_sub.get(str(s.id), [])
                        ],
                    )
                    for s in sub_by_topic.get(str(t.id), [])
                ],
            )
            for t in topics
        ]
    )
