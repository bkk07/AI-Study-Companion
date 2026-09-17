from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.home import (
    HomeAction,
    HomeAttention,
    HomeContinue,
    HomeDay,
    HomeProject,
    HomeRead,
    HomeStats,
)
from app.services import analytics_service, home_service

router = APIRouter(prefix="/me", tags=["me"])


class StreakRead(BaseModel):
    streak_days: int


@router.get("/streak", response_model=StreakRead)
def my_streak(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreakRead:
    """Global study streak: consecutive UTC days with evidence in any project."""
    return StreakRead(streak_days=analytics_service.study_streak_days_global(db, user_id=user.id))


@router.get("/home", response_model=HomeRead)
def my_home(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomeRead:
    """Personalized Home: continue, recent projects, stats, attention, next actions."""
    home = home_service.build_home(db, user_id=user.id)
    return HomeRead(
        continue_=(
            HomeContinue(
                space_id=home.continue_.space_id,
                space_name=home.continue_.space_name,
                project_id=home.continue_.project_id,
                project_name=home.continue_.project_name,
                tab=home.continue_.tab,
                touched_at=home.continue_.touched_at,
            )
            if home.continue_ is not None
            else None
        ),
        recent_projects=[
            HomeProject(
                id=p.id,
                name=p.name,
                space_id=p.space_id,
                space_name=p.space_name,
                progress_pct=p.progress_pct,
                due_count=p.due_count,
                attention_count=p.attention_count,
                touched_at=p.touched_at,
            )
            for p in home.recent_projects
        ],
        stats=HomeStats(
            streak_days=home.stats.streak_days,
            due_total=home.stats.due_total,
            events_week=home.stats.events_week,
            evidence_total=home.stats.evidence_total,
        ),
        attention=[
            HomeAttention(
                project_id=a.project_id,
                project_name=a.project_name,
                space_id=a.space_id,
                concept_id=a.concept_id,
                concept_title=a.concept_title,
                mismatch_type=a.mismatch_type,
                gap=a.gap,
                reason=a.reason,
            )
            for a in home.attention
        ],
        next_actions=[
            HomeAction(
                project_id=a.project_id,
                project_name=a.project_name,
                space_id=a.space_id,
                concept_id=a.concept_id,
                concept_title=a.concept_title,
                action_type=a.action_type,
                score=a.score,
                reasoning=a.reasoning,
                status=a.status,
            )
            for a in home.next_actions
        ],
        week_activity=[HomeDay(day=d.day, events=d.events) for d in home.week_activity],
    )
