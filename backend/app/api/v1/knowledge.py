import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.concept import Concept
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.models.concept_relationship import ConceptRelationship
from app.schemas.knowledge import (
    BrowseConceptRead,
    BrowseSubtopicRead,
    BrowseTopicRead,
    ConceptDetailRead,
    CoverageRead,
    KnowledgeGraphRead,
    KnowledgeTreeRead,
    SearchHitRead,
    SearchResultsRead,
    StreamRead,
)
from app.services import dashboard_service, relationship_service
from app.services.mastery_levels import is_mastery_target, mastery_target_criterion, status_for
from app.services.mastery_service import compute_mastery, mastery_for_concept, mastery_for_concepts
from app.services.rollup_service import (
    display_mastery,
    evidence_total,
)

router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["knowledge"])

SEARCH_MIN_LEN = 2
SEARCH_LIMIT = 20


def _breadcrumb(db: Session, concept: Concept) -> tuple[str, str]:
    sub = db.get(Subtopic, concept.subtopic_id)
    topic = db.get(Topic, sub.topic_id) if sub else None
    return (topic.title if topic else "?", sub.title if sub else "?")


def _hit(db: Session, concept: Concept, user_id: uuid.UUID) -> SearchHitRead:
    topic_title, sub_title = _breadcrumb(db, concept)
    mastery = status = None
    practicable = False
    if is_mastery_target(concept):
        practicable = True
        scores = mastery_for_concept(
            db, user_id=user_id, project_id=concept.project_id, concept_id=concept.id
        )
        mastery = display_mastery(scores)
        status = status_for(mastery)
    return SearchHitRead(
        id=concept.id,
        title=concept.title,
        summary=concept.summary,
        lo_type=concept.type or "CONCEPT",
        importance=concept.importance or "CORE",
        topic=topic_title,
        subtopic=sub_title,
        page_start=concept.page_start,
        page_end=concept.page_end,
        mastery=mastery,
        status=status,
        practicable=practicable,
    )


def _rollup_members(
    members: list[Concept], scores_by_id: dict[uuid.UUID, object]
) -> tuple[float | None, int, int]:
    """In-memory twin of rollup_service.rollup_concepts over precomputed scores.

    Same semantics (practiced = evidence rows > 0; mastery = mean of known
    display values over practiced members; total = target members) with zero
    queries, so the tree no longer re-scores every concept per scope.
    """
    from app.services.mastery_service import MasteryScores

    values: list[float] = []
    practiced = 0
    for concept in sorted(members, key=lambda c: str(c.id)):
        scores = scores_by_id.get(concept.id)
        if not isinstance(scores, MasteryScores):
            continue
        if evidence_total(scores) > 0:
            practiced += 1
            value = display_mastery(scores)
            if value is not None:
                values.append(value)
    mastery = sum(values) / len(values) if values else None
    return mastery, practiced, len(members)


# Scores for a target with zero evidence rows: mastery None, not practiced.
# The batch reader only returns concepts that HAVE evidence, so leaves must
# fall back to this instead of being skipped (skipping hid unevidenced
# concepts from selection entirely).
_EMPTY_SCORES = compute_mastery([])


@router.get("/tree", response_model=KnowledgeTreeRead)
def get_tree(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeTreeRead:
    """Browse hierarchy: CORE mastery targets with mastery + coverage per node.

    Composes the gated dashboard progress (same numbers as the dashboard) over
    the topic tree. SUPPORTING/REFERENCE/obsolete rows never appear here.

    Performance: evidence is read ONCE for the whole project and every scope
    rolls up in memory — the previous per-scope re-scoring issued ~13 queries
    per concept and timed out on real projects (frontend 15s budget).
    """
    concepts = (
        db.query(Concept)
        .filter(Concept.project_id == project.id, mastery_target_criterion())
        .order_by(Concept.created_at.asc())
        .all()
    )
    concepts = [c for c in concepts if is_mastery_target(c)]
    scores_by_id = mastery_for_concepts(db, user_id=user.id, project_id=project.id)
    topics = (
        db.query(Topic).filter(Topic.project_id == project.id)
        .order_by(Topic.created_at.asc()).all()
    )
    subs = (
        db.query(Subtopic).filter(Subtopic.project_id == project.id)
        .order_by(Subtopic.created_at.asc()).all()
    )
    subs_by_topic: dict[uuid.UUID, list[Subtopic]] = {}
    for sub in subs:
        subs_by_topic.setdefault(sub.topic_id, []).append(sub)
    concepts_by_sub: dict[uuid.UUID, list[Concept]] = {}
    for concept in concepts:
        concepts_by_sub.setdefault(concept.subtopic_id, []).append(concept)
    out: list[BrowseTopicRead] = []
    for topic in topics:
        sub_reads: list[BrowseSubtopicRead] = []
        for sub in subs_by_topic.get(topic.id, []):
            leaves: list[BrowseConceptRead] = []
            for row in concepts_by_sub.get(sub.id, []):
                scores = scores_by_id.get(row.id, _EMPTY_SCORES)
                mastery = display_mastery(scores)
                practiced = evidence_total(scores) > 0
                leaves.append(BrowseConceptRead(
                    id=row.id, title=row.title, lo_type=row.type or "CONCEPT",
                    mastery=mastery, status=status_for(mastery), practiced=practiced,
                ))
            mastery, practiced, total = _rollup_members(
                concepts_by_sub.get(sub.id, []), scores_by_id
            )
            sub_reads.append(BrowseSubtopicRead(
                id=sub.id, title=sub.title, core_count=len(leaves),
                coverage=CoverageRead(mastery=mastery, practiced=practiced, total=total),
                concepts=leaves,
            ))
        members = [c for sub in subs_by_topic.get(topic.id, []) for c in concepts_by_sub.get(sub.id, [])]
        mastery, practiced, total = _rollup_members(members, scores_by_id)
        out.append(BrowseTopicRead(
            id=topic.id, title=topic.title,
            core_count=sum(s.core_count for s in sub_reads),
            coverage=CoverageRead(mastery=mastery, practiced=practiced, total=total),
            subtopics=sub_reads,
        ))
    all_members = list(concepts)
    mastery, practiced, total = _rollup_members(all_members, scores_by_id)
    return KnowledgeTreeRead(
        topics=out,
        overall=CoverageRead(mastery=mastery, practiced=practiced, total=total),
    )


@router.get("/search", response_model=SearchResultsRead)
def search(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=SEARCH_MIN_LEN, max_length=200),
) -> SearchResultsRead:
    """Project-scoped search across ALL importances (knowledge model).

    Supporting/reference knowledge is discoverable here by design — only
    CORE rows are practicable. ILIKE v1 (no trigram infra yet).
    """
    needle = f"%{q.strip()}%"
    rows = (
        db.query(Concept)
        .filter(
            Concept.project_id == project.id,
            (Concept.title.ilike(needle)) | (Concept.summary.ilike(needle)),
        )
        .order_by(Concept.created_at.asc())
        .limit(SEARCH_LIMIT)
        .all()
    )
    return SearchResultsRead(query=q.strip(), hits=[_hit(db, row, user.id) for row in rows])


@router.get("/graph", response_model=KnowledgeGraphRead)
def get_graph(
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeGraphRead:
    """Mini-map: CORE concept nodes with mastery + semantic edges. Reads only.

    Nodes reuse the gated dashboard progress (same mastery as everywhere);
    edges are the stored PREREQUISITE_OF / RELATED_TO links between project
    concepts, capped so large maps stay renderable.
    """
    from app.schemas.knowledge import GraphEdgeRead, GraphNodeRead

    progress, _ = dashboard_service.build_dashboard(db, user_id=user.id, project_id=project.id)
    by_id = {p.concept_id: p for p in progress}
    topics = {t.id: t.title for t in db.query(Topic).filter(Topic.project_id == project.id).all()}
    subs = {s.id: s for s in db.query(Subtopic).filter(Subtopic.project_id == project.id).all()}
    nodes = []
    for p in progress:
        concept = db.get(Concept, p.concept_id)
        sub = subs.get(concept.subtopic_id) if concept else None
        nodes.append(GraphNodeRead(
            id=p.concept_id,
            title=p.title,
            topic=topics.get(sub.topic_id, "?") if sub else "?",
            mastery=display_mastery(p.scores),
            status=status_for(display_mastery(p.scores)),
        ))
    owned = {p.concept_id for p in progress}
    if not owned:
        return KnowledgeGraphRead(nodes=nodes, edges=[])
    edge_rows = (
        db.query(ConceptRelationship)
        .filter(
            ConceptRelationship.from_concept_id.in_(owned),
            ConceptRelationship.to_concept_id.in_(owned),
            ConceptRelationship.relation.in_(("PREREQUISITE_OF", "RELATED_TO")),
        )
        .order_by(ConceptRelationship.created_at.asc())
        .limit(300)
        .all()
    )
    return KnowledgeGraphRead(
        nodes=nodes,
        edges=[GraphEdgeRead(from_id=e.from_concept_id, to_id=e.to_concept_id, relation=e.relation)
               for e in edge_rows],
    )


@router.get("/concepts/{concept_id}", response_model=ConceptDetailRead)
def get_concept_detail(
    concept_id: uuid.UUID,
    project: Project = Depends(get_authorized_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConceptDetailRead:
    """Concept-detail aggregate: mastery, history, relations, source."""
    concept = db.get(Concept, concept_id)
    if concept is None or concept.project_id != project.id:
        raise HTTPException(status_code=404, detail="concept not found in this project")
    scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                 concept_id=concept.id)
    answers = (
        db.query(QuizAnswer.is_correct, QuizAnswer.answered_at)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(QuizQuestion, QuizAnswer.question_id == QuizQuestion.id)
        .join(Quiz, QuizQuestion.quiz_id == Quiz.id)
        .filter(QuizAttempt.user_id == user.id, Quiz.project_id == project.id,
                QuizQuestion.concept_id == concept.id)
        .all()
    )
    attempted = len(answers)
    correct = sum(1 for ok, _ in answers if ok)
    lasts = [at for _, at in answers]
    lasts += [s.last_at for s in (scores.quiz, scores.open_ended, scores.practice,
                                  scores.flashcard, scores.tutor) if s.last_at is not None]
    last_at = max(lasts) if lasts else None

    related = relationship_service.get_related(db, concept.id)
    by_id = {c.id: c for c in db.query(Concept).filter(
        Concept.project_id == project.id).all()}

    def _rel_hit(edge: dict) -> SearchHitRead | None:
        row = by_id.get(uuid.UUID(edge["concept_id"]))
        return _hit(db, row, user.id) if row is not None else None

    prerequisites = [h for h in (_rel_hit(e) for e in related["prerequisites"]) if h]
    related_hits = [h for h in (_rel_hit(e) for e in related["related"]) if h]
    supporting = [
        _hit(db, row, user.id)
        for row in db.query(Concept).filter(
            Concept.subtopic_id == concept.subtopic_id, Concept.id != concept.id
        ).order_by(Concept.created_at.asc()).all()
        if (row.importance or "CORE") != "CORE"
        and (row.meta or {}).get("status") != "obsolete"
    ][:10]

    material_name = None
    if concept.material_id is not None:
        mat = db.get(Material, concept.material_id)
        material_name = mat.filename if mat else None
    mastery = display_mastery(scores)
    return ConceptDetailRead(
        id=concept.id, title=concept.title, summary=concept.summary,
        lo_type=concept.type or "CONCEPT", importance=concept.importance or "CORE",
        mastery=mastery, status=status_for(mastery),
        mcq=StreamRead(value=scores.mcq.value, count=scores.mcq.count),
        applied=StreamRead(value=scores.applied.value, count=scores.applied.count),
        final_mastery=scores.final,
        evidence_confidence=scores.evidence_confidence,
        streams={
            name: StreamRead(value=getattr(scores, name).value,
                             count=getattr(scores, name).count)
            for name in ("quiz", "open_ended", "practice", "flashcard", "tutor")
        },
        questions_attempted=attempted, questions_correct=correct,
        last_practiced_at=last_at,
        prerequisites=prerequisites, related=related_hits, supporting=supporting,
        source_material=material_name,
        page_start=concept.page_start, page_end=concept.page_end,
    )
