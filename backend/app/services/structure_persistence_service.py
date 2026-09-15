"""Persist validated learning outlines — Phase 25.

Upserts Topic → Subtopic → Concept rows scoped to a project. Identity is the
stripped case-insensitive title within the parent scope, so re-processing the
same material updates rows in place instead of duplicating trees. Single
commit; rollback on any error (no partial trees).
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.project import Project
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.schemas.structure import StructureOutline


def _norm(title: str) -> str:
    return title.strip()


def persist_structure(
    db: Session, project_id: uuid.UUID, outline: StructureOutline
) -> dict[str, int]:
    """Upsert outline for project. Returns total counts {topics, subtopics, concepts}."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        existing_topics = db.query(Topic).filter(Topic.project_id == project_id).all()
        topic_map = {_norm(t.title).lower(): t for t in existing_topics}

        for t_in in outline.topics:
            t_title = _norm(t_in.title)
            topic = topic_map.get(t_title.lower())
            if topic is None:
                topic = Topic(project_id=project_id, title=t_title)
                db.add(topic)
                db.flush()
                topic_map[t_title.lower()] = topic
            elif topic.title != t_title:
                topic.title = t_title
                db.flush()

            existing_subs = db.query(Subtopic).filter(Subtopic.topic_id == topic.id).all()
            sub_map = {_norm(s.title).lower(): s for s in existing_subs}
            for s_in in t_in.subtopics:
                s_title = _norm(s_in.title)
                sub = sub_map.get(s_title.lower())
                if sub is None:
                    sub = Subtopic(project_id=project_id, topic_id=topic.id, title=s_title)
                    db.add(sub)
                    db.flush()
                    sub_map[s_title.lower()] = sub
                elif sub.title != s_title:
                    sub.title = s_title
                    db.flush()

                existing_cons = db.query(Concept).filter(Concept.subtopic_id == sub.id).all()
                con_map = {_norm(c.title).lower(): c for c in existing_cons}
                for c_in in s_in.concepts:
                    c_title = _norm(c_in.title)
                    c_summary = c_in.summary.strip()
                    con = con_map.get(c_title.lower())
                    if con is None:
                        con = Concept(
                            project_id=project_id,
                            subtopic_id=sub.id,
                            title=c_title,
                            summary=c_summary,
                        )
                        db.add(con)
                        db.flush()
                        con_map[c_title.lower()] = con
                    else:
                        if con.title != c_title:
                            con.title = c_title
                        if con.summary != c_summary:
                            con.summary = c_summary
                        db.flush()

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "topics": db.query(Topic).filter(Topic.project_id == project_id).count(),
        "subtopics": db.query(Subtopic).filter(Subtopic.project_id == project_id).count(),
        "concepts": db.query(Concept).filter(Concept.project_id == project_id).count(),
    }
