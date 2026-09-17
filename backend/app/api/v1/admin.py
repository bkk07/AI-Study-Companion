import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.admin import get_current_admin
from app.models.ai_usage import AIUsage
from app.models.background_job import BackgroundJob
from app.models.learning_event import LearningEvent
from app.models.mastery_evidence import MasteryEvidence
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.recommendation import Recommendation
from app.models.space import Space
from app.models.user import User
from app.schemas.admin import (
    ActivityEventRead,
    ActivityPage,
    AdminOverview,
    AdminUserRead,
    AIUsageDayRow,
    AIUsageSummary,
    AIUsageTopError,
    HealthLLMError,
    HealthJob,
    HealthRead,
    JobsByStatus,
    JourneyAttempt,
    JourneyProject,
    MasterySummary,
    SpendSummary,
    UserJourney,
    UsersPage,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UsersPage)
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="email substring filter"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> UsersPage:
    """Paginated users with project count + last tracked activity. No password hashes."""
    query = db.query(User)
    if q is not None and q.strip():
        query = query.filter(User.email.ilike(f"%{q.strip()[:120]}%"))
    total = query.count()
    rows = query.order_by(User.created_at.asc()).offset(offset).limit(limit).all()
    ids = [u.id for u in rows]
    proj_counts: dict = (
        dict(
            db.query(Space.user_id, func.count(Project.id))
            .join(Project, Project.space_id == Space.id)
            .filter(Space.user_id.in_(ids))
            .group_by(Space.user_id)
            .all()
        )
        if ids
        else {}
    )
    last_seen: dict = (
        dict(
            db.query(LearningEvent.user_id, func.max(LearningEvent.created_at))
            .filter(LearningEvent.user_id.in_(ids))
            .group_by(LearningEvent.user_id)
            .all()
        )
        if ids
        else {}
    )
    return UsersPage(
        items=[
            AdminUserRead(
                id=u.id,
                email=u.email,
                is_admin=u.is_admin,
                created_at=u.created_at,
                project_count=proj_counts.get(u.id, 0),
                last_active=last_seen.get(u.id),
            )
            for u in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/overview", response_model=AdminOverview)
def usage_overview(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminOverview:
    """Global table counts for operations. Single queries, no PII."""
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    cost_week = (
        db.query(func.sum(AIUsage.cost_usd))
        .filter(AIUsage.created_at >= week_ago)
        .scalar()
    )
    return AdminOverview(
        users=db.query(func.count(User.id)).scalar() or 0,
        spaces=db.query(func.count(Space.id)).scalar() or 0,
        projects=db.query(func.count(Project.id)).scalar() or 0,
        materials=db.query(func.count(Material.id)).scalar() or 0,
        quizzes=db.query(func.count(Quiz.id)).scalar() or 0,
        quiz_attempts=db.query(func.count(QuizAttempt.id)).scalar() or 0,
        evidence_rows=db.query(func.count(MasteryEvidence.id)).scalar() or 0,
        recommendations=db.query(func.count(Recommendation.id)).scalar() or 0,
        quiz_attempts_week=db.query(func.count(QuizAttempt.id))
        .filter(QuizAttempt.created_at >= week_ago)
        .scalar()
        or 0,
        cost_week_usd=float(cost_week) if cost_week is not None else None,
    )


@router.get("/activity", response_model=ActivityPage)
def list_activity(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    user_id: uuid.UUID | None = None,
    space_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    type: str | None = Query(default=None, description="event_type, e.g. quiz.completed"),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ActivityPage:
    """Paginated learning events, newest first. All filters are query params."""
    q = db.query(LearningEvent)
    if user_id is not None:
        q = q.filter(LearningEvent.user_id == user_id)
    if space_id is not None:
        q = q.filter(LearningEvent.space_id == space_id)
    if project_id is not None:
        q = q.filter(LearningEvent.project_id == project_id)
    if type is not None:
        q = q.filter(LearningEvent.event_type == type)
    if since is not None:
        q = q.filter(LearningEvent.created_at >= since)
    if until is not None:
        q = q.filter(LearningEvent.created_at <= until)
    total = q.count()
    rows = (
        q.order_by(LearningEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ActivityPage(
        items=[ActivityEventRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/ai-usage", response_model=AIUsageSummary)
def ai_usage_summary(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    feature: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> AIUsageSummary:
    """Tokens + cost grouped by feature × provider × model × day, with latency and errors (§14)."""
    base = db.query(AIUsage)
    if feature is not None:
        base = base.filter(AIUsage.feature == feature)
    if provider is not None:
        base = base.filter(AIUsage.provider == provider)
    if model is not None:
        base = base.filter(AIUsage.model == model)
    if since is not None:
        base = base.filter(AIUsage.created_at >= since)
    if until is not None:
        base = base.filter(AIUsage.created_at <= until)

    totals = base.with_entities(
        func.count(AIUsage.id),
        func.coalesce(func.sum(AIUsage.prompt_tokens), 0),
        func.coalesce(func.sum(AIUsage.completion_tokens), 0),
        func.sum(AIUsage.cost_usd),
    ).first()
    _calls = totals[0] or 0
    _prompt = int(totals[1] or 0)
    _completion = int(totals[2] or 0)
    _cost = float(totals[3]) if totals[3] is not None else None

    failed = base.filter(AIUsage.success.is_(False)).count()
    error_rate = (failed / _calls) if _calls else 0.0

    lat = (
        base.filter(AIUsage.latency_ms.is_not(None))
        .with_entities(
            func.percentile_cont(0.5).within_group(AIUsage.latency_ms),
            func.percentile_cont(0.95).within_group(AIUsage.latency_ms),
        )
        .first()
    )
    p50 = float(lat[0]) if lat and lat[0] is not None else None
    p95 = float(lat[1]) if lat and lat[1] is not None else None

    top = (
        base.filter(AIUsage.success.is_(False), AIUsage.error_type.is_not(None))
        .with_entities(AIUsage.error_type, func.count(AIUsage.id))
        .group_by(AIUsage.error_type)
        .order_by(func.count(AIUsage.id).desc())
        .limit(10)
        .all()
    )

    day = func.date_trunc("day", AIUsage.created_at).label("day")
    grouped = (
        base.with_entities(
            day,
            AIUsage.feature,
            AIUsage.provider,
            AIUsage.model,
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.prompt_tokens), 0),
            func.coalesce(func.sum(AIUsage.completion_tokens), 0),
            func.sum(AIUsage.cost_usd),
            func.avg(AIUsage.latency_ms),
        )
        .group_by(day, AIUsage.feature, AIUsage.provider, AIUsage.model)
        .order_by(day.desc())
        .limit(500)
        .all()
    )
    return AIUsageSummary(
        calls=_calls,
        prompt_tokens=_prompt,
        completion_tokens=_completion,
        cost_usd=_cost,
        error_rate=error_rate,
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        top_errors=[AIUsageTopError(error_type=t[0], count=t[1]) for t in top],
        rows=[
            AIUsageDayRow(
                day=r[0].date().isoformat() if hasattr(r[0], "date") else str(r[0]),
                feature=r[1],
                provider=r[2],
                model=r[3],
                calls=r[4],
                prompt_tokens=int(r[5] or 0),
                completion_tokens=int(r[6] or 0),
                cost_usd=float(r[7]) if r[7] is not None else None,
                avg_latency_ms=float(r[8]) if r[8] is not None else None,
            )
            for r in grouped
        ],
    )


@router.get("/users/{user_id}/journey", response_model=UserJourney)
def user_journey(
    user_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> UserJourney:
    """Inspect one learner: projects, event timeline, attempts, mastery, AI spend."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    spaces = db.query(Space).filter(Space.user_id == target.id).all()
    space_ids = [s.id for s in spaces]
    projects = (
        db.query(Project)
        .filter(Project.space_id.in_(space_ids))
        .order_by(Project.created_at.asc())
        .all()
        if space_ids
        else []
    )
    events = (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == target.id)
        .order_by(LearningEvent.created_at.desc())
        .limit(50)
        .all()
    )
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == target.id)
        .order_by(QuizAttempt.started_at.desc().nullslast(), QuizAttempt.created_at.desc())
        .limit(20)
        .all()
    )
    ev_rows = db.query(MasteryEvidence).filter(MasteryEvidence.user_id == target.id).all()
    by_type: dict[str, int] = {}
    scores = []
    for e in ev_rows:
        by_type[e.evidence_type] = by_type.get(e.evidence_type, 0) + 1
        if e.raw_score is not None:
            scores.append(float(e.raw_score))
    spend = (
        db.query(
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.prompt_tokens), 0),
            func.coalesce(func.sum(AIUsage.completion_tokens), 0),
            func.sum(AIUsage.cost_usd),
        )
        .filter(AIUsage.user_id == target.id)
        .first()
    )
    return UserJourney(
        user_id=target.id,
        email=target.email,
        projects=[
            JourneyProject(id=p.id, name=p.name, space_id=p.space_id, created_at=p.created_at)
            for p in projects
        ],
        recent_events=[ActivityEventRead.model_validate(e) for e in events],
        recent_attempts=[
            JourneyAttempt(
                id=a.id,
                quiz_id=a.quiz_id,
                score=float(a.score) if a.score is not None else None,
                started_at=a.started_at,
                completed_at=a.completed_at,
            )
            for a in attempts
        ],
        mastery=MasterySummary(
            evidence_rows=len(ev_rows),
            by_type=by_type,
            avg_score=(sum(scores) / len(scores)) if scores else None,
        ),
        spend=SpendSummary(
            calls=spend[0] or 0,
            prompt_tokens=int(spend[1] or 0),
            completion_tokens=int(spend[2] or 0),
            cost_usd=float(spend[3]) if spend[3] is not None else None,
        ),
    )


@router.get("/health", response_model=HealthRead)
def system_health(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> HealthRead:
    """Which workflow failed / why was it slow (§14): recent job + LLM failures."""
    failed_jobs = (
        db.query(BackgroundJob)
        .filter(BackgroundJob.status == "failed")
        .order_by(BackgroundJob.created_at.desc())
        .limit(limit)
        .all()
    )
    failed_llm = (
        db.query(AIUsage)
        .filter(AIUsage.success.is_(False))
        .order_by(AIUsage.created_at.desc())
        .limit(limit)
        .all()
    )
    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_job_24h = (
        db.query(func.count(BackgroundJob.id))
        .filter(BackgroundJob.status == "failed", BackgroundJob.created_at >= day_ago)
        .scalar()
        or 0
    )
    failed_llm_24h = (
        db.query(func.count(AIUsage.id))
        .filter(AIUsage.success.is_(False), AIUsage.created_at >= day_ago)
        .scalar()
        or 0
    )
    by_status = (
        db.query(BackgroundJob.status, func.count(BackgroundJob.id))
        .group_by(BackgroundJob.status)
        .all()
    )
    return HealthRead(
        failed_jobs=[HealthJob.model_validate(j) for j in failed_jobs],
        failed_llm_calls=[HealthLLMError.model_validate(c) for c in failed_llm],
        failed_job_count_24h=failed_job_24h,
        failed_llm_count_24h=failed_llm_24h,
        jobs_by_status=[JobsByStatus(status=s, count=c) for s, c in by_status],
    )
