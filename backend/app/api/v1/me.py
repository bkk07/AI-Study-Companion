from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services import analytics_service

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
