"""Persist validated learning outlines — Phase 25.

Upserts Topic → Subtopic → Concept rows scoped to a project. Identity is the
stripped case-insensitive title within the parent scope, so re-processing the
same material updates rows in place instead of duplicating trees. Single
commit; rollback on any error (no partial trees).
"""

import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.concept import OBSOLETE_STATUS, Concept
from app.models.concept_relationship import ConceptRelationship
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import QuizQuestion
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.schemas.structure import (
    LearningObjectOutline,
    StructureOutline,
    TopicLearningObjects,
    TopicSpanOutline,
)



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


# --- Knowledge-map persist (Phase B): identity-preserving two-pass writes ----

# Soft quality guideline (design §5/§8): 2–8 CORE objects per subtopic.
# Advisory only — reported in the job result, never enforced, nothing dropped.
CORE_GUIDELINE_MIN = 2
CORE_GUIDELINE_MAX = 8
# Stored semantic edges per object (design §7). Proposals beyond the cap are
# dropped with a count in the result; the job never fails over this.
MAX_STORED_EDGES_PER_OBJECT = 5


def _alnum_fold(title: str) -> str:
    """Lowercase alphanumeric folding for near-duplicate detection.

    "k-NN" and "kNN" fold equal; "Label" and "Label/Target" do not (that is a
    split, not a duplicate — never merged).
    """
    return re.sub(r"[^a-z0-9]", "", title.lower())


def _is_obsolete(concept: Concept) -> bool:
    return isinstance(concept.meta, dict) and concept.meta.get("status") == OBSOLETE_STATUS


def _evidence_count(db: Session, concept_id: uuid.UUID) -> int:
    """History weight for merge decisions: evidence + question rows."""
    ev = db.query(MasteryEvidence).filter(MasteryEvidence.concept_id == concept_id).count()
    qq = db.query(QuizQuestion).filter(QuizQuestion.concept_id == concept_id).count()
    return ev + qq


def _apply_lo_fields(
    con: Concept, lo: LearningObjectOutline, material_id: uuid.UUID | None
) -> None:
    """Update a matched row in place (same id → history intact)."""
    con.title = lo.name.strip()
    con.summary = lo.summary.strip()
    con.type = lo.type
    con.importance = lo.importance
    con.page_start = lo.page_start
    con.page_end = lo.page_end
    meta = dict(con.meta or {})
    if lo.section:
        meta["source_section"] = lo.section
    meta["extraction_pass"] = 2
    # Provenance stewardship: stamp the producing material only when unknown;
    # never overwrite another material's stamp (shared subtopics).
    if material_id is not None and con.material_id is None:
        con.material_id = material_id
    for key in ("status", "obsolete_at", "merged_into"):
        meta.pop(key, None)
    con.meta = meta


def _mark_obsolete(con: Concept, *, merged_into: uuid.UUID | None = None) -> None:
    """Flag a row obsolete without deleting it — history FKs stay valid."""
    meta = dict(con.meta or {})
    meta["status"] = OBSOLETE_STATUS
    meta["obsolete_at"] = datetime.now(timezone.utc).isoformat()
    if merged_into is not None:
        meta["merged_into"] = str(merged_into)
    con.meta = meta


def _insensitive_hit(rows: list, title: str):
    """Exact-then-case-insensitive title match in Python (avoids LIKE wildcards)."""
    wanted = _norm(title)
    for row in rows:
        if _norm(row.title) == wanted:
            return row
    lowered = wanted.lower()
    for row in rows:
        if _norm(row.title).lower() == lowered:
            return row
    return None


def _get_or_create_topic(db: Session, project_id: uuid.UUID, title: str) -> Topic:
    topic = _insensitive_hit(
        db.query(Topic).filter(Topic.project_id == project_id).all(), title
    )
    if topic is None:
        topic = Topic(project_id=project_id, title=_norm(title))
        db.add(topic)
        db.flush()
    elif topic.title != _norm(title):
        topic.title = _norm(title)
        db.flush()
    return topic


def _get_or_create_sub(
    db: Session, project_id: uuid.UUID, topic: Topic, s_title: str
) -> Subtopic:
    sub = _insensitive_hit(
        db.query(Subtopic).filter(Subtopic.topic_id == topic.id).all(), s_title
    )
    if sub is None:
        sub = Subtopic(project_id=project_id, topic_id=topic.id, title=_norm(s_title))
        db.add(sub)
        db.flush()
    elif sub.title != _norm(s_title):
        sub.title = _norm(s_title)
        db.flush()
    return sub


def _resolve_lo_subtopic(
    db: Session,
    project_id: uuid.UUID,
    topic: Topic,
    span: TopicSpanOutline,
    sub_rows: dict,
    lo_sub_name: str,
) -> Subtopic:
    """Route an LO to its named subtopic; materialize unknown names under the topic.

    Unknown names become real subtopics (topic span) rather than dropping
    genuine objects or misfiling them under a wrong subtopic.
    """
    key = (_norm(span.title).lower(), _norm(lo_sub_name).lower())
    sub = sub_rows.get(key)
    if sub is None:
        sub = _get_or_create_sub(db, project_id, topic, lo_sub_name)
        sub_rows[key] = sub
    return sub


def _active_in_sub(db: Session, sub_id: uuid.UUID) -> list[Concept]:
    return [
        c for c in db.query(Concept).filter(Concept.subtopic_id == sub_id).all()
        if not _is_obsolete(c)
    ]


def _match_or_create_lo(
    db: Session,
    topic: Topic,
    sub: Subtopic,
    topic_sub_ids: list[uuid.UUID],
    lo: LearningObjectOutline,
    material_id: uuid.UUID | None,
    matched_ids: set[uuid.UUID],
) -> Concept:
    """Design §9 identity rule: exact → topic-scope move → alnum-merge → insert."""
    norm = _norm(lo.name).lower()
    here = sorted(_active_in_sub(db, sub.id), key=lambda c: c.created_at)
    by_norm: dict[str, Concept] = {}
    for c in here:
        by_norm.setdefault(_norm(c.title).lower(), c)

    # Rule 1: exact (subtopic, title) hit → update in place, same id.
    hit = by_norm.get(norm)
    if hit is not None:
        _apply_lo_fields(hit, lo, material_id)
        db.flush()
        return hit

    # Rule 1b: exact hit on an obsolete row → revive it (never duplicate).
    for c in db.query(Concept).filter(Concept.subtopic_id == sub.id).all():
        if _is_obsolete(c) and _norm(c.title).lower() == norm:
            _apply_lo_fields(c, lo, material_id)
            db.flush()
            return c

    # Rule 2: topic-scope hit in a sibling subtopic → move the row, keep id.
    for row in (
        db.query(Concept).filter(Concept.subtopic_id.in_(topic_sub_ids)).all()
    ):
        if row.subtopic_id == sub.id or _is_obsolete(row):
            continue
        if _norm(row.title).lower() == norm:
            # Free the exact-UQ slot if an obsolete row squats on it.
            for squatter in db.query(Concept).filter(Concept.subtopic_id == sub.id).all():
                if (
                    _is_obsolete(squatter)
                    and _norm(squatter.title) == _norm(lo.name)
                    and squatter.id != row.id
                ):
                    squatter.title = f"{squatter.title} (superseded)"
            row.subtopic_id = sub.id
            _apply_lo_fields(row, lo, material_id)
            db.flush()
            return row

    # Rule 3: same-subtopic alnum-fold duplicate ("k-NN"/"kNN") → merge into
    # the most-evidenced row; losers are flagged, never deleted. Never merges
    # on mere similarity: folding must be identical and non-trivial.
    fold = _alnum_fold(lo.name)
    if len(fold) >= 3:
        dups = [c for c in here if _alnum_fold(c.title) == fold]
        if dups:
            weights = {c.id: _evidence_count(db, c.id) for c in dups}
            best = max(weights.values())
            # Most evidence wins; ties → smallest title (deterministic).
            winner = min((c for c in dups if weights[c.id] == best), key=lambda c: c.title)
            _apply_lo_fields(winner, lo, material_id)
            for loser in dups:
                if loser.id != winner.id:
                    _mark_obsolete(loser, merged_into=winner.id)
            db.flush()
            return winner

    # Rule 4: genuinely new object → insert.
    con = Concept(
        project_id=sub.project_id,
        subtopic_id=sub.id,
        title=_norm(lo.name),
        summary=lo.summary.strip(),
        type=lo.type,
        importance=lo.importance,
        page_start=lo.page_start,
        page_end=lo.page_end,
        material_id=material_id,
        meta={"source_section": lo.section, "extraction_pass": 2}
        if lo.section
        else {"extraction_pass": 2},
    )
    db.add(con)
    db.flush()
    return con


def _find_active_lo(
    db: Session,
    project_id: uuid.UUID,
    topic_id: uuid.UUID,
    subtopic_id: uuid.UUID | None,
    name: str,
    exclude_id: uuid.UUID | None = None,
) -> Concept | None:
    """Resolve an edge-proposal name to a row: subtopic → topic → project."""
    norm = _norm(name).lower()
    scopes = []
    if subtopic_id is not None:
        scopes.append(Concept.subtopic_id == subtopic_id)
    scopes.append(Concept.subtopic_id.in_(
        [s.id for s in db.query(Subtopic).filter(Subtopic.topic_id == topic_id).all()]
    ))
    scopes.append(Concept.project_id == project_id)
    for criterion in scopes:
        q = db.query(Concept).filter(criterion)
        if exclude_id is not None:
            q = q.filter(Concept.id != exclude_id)
        for row in q.order_by(Concept.created_at.asc()).all():
            if _is_obsolete(row):
                continue
            if _norm(row.title).lower() == norm:
                return row
    return None


def _obsolete_unmatched(
    db: Session,
    project_id: uuid.UUID,
    material_id: uuid.UUID | None,
    touched_sub_ids: set[uuid.UUID],
    matched_ids: set[uuid.UUID],
) -> list[str]:
    """Flag stale rows obsolete (visible, reversible, never deleted).

    Scope: rows stamped with this material anywhere, plus legacy NULL-material
    rows inside touched subtopics (overwhelmingly this material's own earlier
    map). Untouched subtopics are never swept.
    """
    titles: list[str] = []
    q = db.query(Concept).filter(Concept.project_id == project_id)
    if material_id is not None:
        q = q.filter(
            (Concept.material_id == material_id)
            | (
                Concept.material_id.is_(None)
                & Concept.subtopic_id.in_(touched_sub_ids)
            )
        )
    elif touched_sub_ids:
        q = q.filter(
            Concept.material_id.is_(None) & Concept.subtopic_id.in_(touched_sub_ids)
        )
    else:
        return titles
    for row in q.all():
        if row.id in matched_ids or _is_obsolete(row):
            continue
        _mark_obsolete(row)
        titles.append(row.title)
    db.flush()
    return titles


def _core_guideline_notes(
    db: Session, project_id: uuid.UUID, touched_sub_ids: set[uuid.UUID]
) -> list[str]:
    """Soft 2–8 CORE/subtopic signal (advisory; nothing is dropped)."""
    notes: list[str] = []
    if not touched_sub_ids:
        return notes
    subs = db.query(Subtopic).filter(Subtopic.id.in_(touched_sub_ids)).all()
    topics = {t.id: t.title for t in db.query(Topic).filter(
        Topic.project_id == project_id).all()}
    for sub in sorted(subs, key=lambda s: s.title):
        core = sum(
            1 for c in _active_in_sub(db, sub.id) if (c.importance or "CORE") == "CORE"
        )
        if core < CORE_GUIDELINE_MIN or core > CORE_GUIDELINE_MAX:
            notes.append(
                f"{topics.get(sub.topic_id, '?')} / {sub.title}: {core} CORE targets "
                f"(guideline {CORE_GUIDELINE_MIN}-{CORE_GUIDELINE_MAX})"
            )
    return notes


def persist_knowledge_map(
    db: Session,
    *,
    project_id: uuid.UUID,
    material_id: uuid.UUID | None,
    topic_map: "TopicMapOutline",
    topic_results: "list[tuple[TopicSpanOutline, TopicLearningObjects | None]]",
) -> dict:
    """Persist a two-pass knowledge map with identity preservation (Phase B).

    Upserts topics/subtopics (same title rules as the legacy path), then
    upserts learning objects via the design §9 identity rule:
      1. (subtopic, normalized title) exact hit → update in place (same id);
         an obsolete row hit here is revived, never duplicated;
      2. (topic scope, normalized title) hit in a sibling subtopic → move the
         row, keep the id;
      3. same-subtopic alnum-fold duplicate (e.g. "k-NN"/"kNN") → merge, keep
         the most-evidenced id, obsolete the loser (never delete);
      4. otherwise insert.
    Rows of this material (plus legacy NULL-material rows in touched
    subtopics) that match nothing are flagged obsolete — reported visibly,
    never deleted. Semantic edge proposals resolve to ids (subtopic → topic
    → project); unresolvable names and over-cap edges are dropped with
    counts. Single commit; rollback on any error.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    matched_ids: set[uuid.UUID] = set()
    touched_sub_ids: set[uuid.UUID] = set()
    obsoleted_titles: list[str] = []
    dropped_edges = 0
    new_edge_count = 0

    try:
        # --- structure upsert (topics/subtopics), flushed for ids --------------
        topic_rows: dict[str, Topic] = {}
        sub_rows: dict[tuple[str, str], Subtopic] = {}
        for span, _ in topic_results:
            topic = _get_or_create_topic(db, project_id, span.title)
            topic_rows[_norm(span.title).lower()] = topic

            # Pass-1 subtopics first (listed order), then any LO-named extras.
            ordered_subs = [s.title for s in span.subtopics]
            for s_title in ordered_subs:
                sub = _get_or_create_sub(db, project_id, topic, s_title)
                sub_rows[(_norm(span.title).lower(), _norm(s_title).lower())] = sub
                touched_sub_ids.add(sub.id)

        # --- learning-object upsert -------------------------------------------
        for span, lo_result in topic_results:
            topic = topic_rows[_norm(span.title).lower()]
            if lo_result is None:
                continue  # Pass 2 failed for this topic: structure kept, no LOs
            topic_sub_ids = [
                s.id for s in db.query(Subtopic).filter(Subtopic.topic_id == topic.id).all()
            ]
            for lo in lo_result.objects:
                sub = _resolve_lo_subtopic(
                    db, project_id, topic, span, sub_rows, lo.subtopic
                )
                touched_sub_ids.add(sub.id)
                if lo.name is None:
                    continue
                con = _match_or_create_lo(
                    db, topic, sub, topic_sub_ids, lo, material_id, matched_ids
                )
                matched_ids.add(con.id)

        db.flush()

        # --- semantic edges (resolve proposals to ids) -------------------------
        for span, lo_result in topic_results:
            if lo_result is None:
                continue
            topic = topic_rows[_norm(span.title).lower()]
            for lo in lo_result.objects:
                if not lo.relationships:
                    continue
                from_row = _find_active_lo(db, project_id, topic.id, None, lo.name)
                if from_row is None:
                    continue
                existing = {
                    (r.to_concept_id, r.relation)
                    for r in db.query(ConceptRelationship).filter(
                        ConceptRelationship.from_concept_id == from_row.id
                    ).all()
                }
                stored = len(existing)
                for prop in lo.relationships:
                    if stored >= MAX_STORED_EDGES_PER_OBJECT:
                        dropped_edges += 1
                        continue
                    to_row = _find_active_lo(
                        db, project_id, topic.id, from_row.subtopic_id, prop.to_name,
                        exclude_id=from_row.id,
                    )
                    if to_row is None or (to_row.id, prop.relation) in existing:
                        dropped_edges += 1
                        continue
                    db.add(ConceptRelationship(
                        from_concept_id=from_row.id,
                        to_concept_id=to_row.id,
                        relation=prop.relation,
                        evidence_span=prop.evidence_span,
                        created_by="llm",
                    ))
                    existing.add((to_row.id, prop.relation))
                    stored += 1
                    new_edge_count += 1
        db.flush()

        # --- obsolete sweep (flag, never delete) --------------------------------
        obsoleted_titles = _obsolete_unmatched(
            db, project_id, material_id, touched_sub_ids, matched_ids
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "topics": db.query(Topic).filter(Topic.project_id == project_id).count(),
        "subtopics": db.query(Subtopic).filter(Subtopic.project_id == project_id).count(),
        "concepts": db.query(Concept).filter(Concept.project_id == project_id).count(),
        "relationships": db.query(ConceptRelationship).join(
            Concept, ConceptRelationship.from_concept_id == Concept.id
        ).filter(Concept.project_id == project_id).count(),
        "obsoleted": len(obsoleted_titles),
        "obsoleted_titles": obsoleted_titles,
        "dropped_edges": dropped_edges,
        "new_relationships": new_edge_count,
        "guideline_notes": _core_guideline_notes(db, project_id, touched_sub_ids),
    }
