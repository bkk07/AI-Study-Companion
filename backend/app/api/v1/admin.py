from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.admin import get_current_admin
from app.models.mastery_evidence import MasteryEvidence
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.recommendation import Recommendation
from app.models.space import Space
from app.models.user import User
from app.schemas.admin import AdminOverview
from app.schemas.user import UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    """All users, oldest first. Password hashes never leave the server."""
    return db.query(User).order_by(User.created_at.asc()).all()


@router.get("/overview", response_model=AdminOverview)
def usage_overview(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminOverview:
    """Global table counts for operations. Single queries, no PII."""
    return AdminOverview(
        users=db.query(func.count(User.id)).scalar() or 0,
        spaces=db.query(func.count(Space.id)).scalar() or 0,
        projects=db.query(func.count(Project.id)).scalar() or 0,
        materials=db.query(func.count(Material.id)).scalar() or 0,
        quizzes=db.query(func.count(Quiz.id)).scalar() or 0,
        quiz_attempts=db.query(func.count(QuizAttempt.id)).scalar() or 0,
        evidence_rows=db.query(func.count(MasteryEvidence.id)).scalar() or 0,
        recommendations=db.query(func.count(Recommendation.id)).scalar() or 0,
    )
