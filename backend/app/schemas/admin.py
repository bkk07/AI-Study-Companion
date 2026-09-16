from pydantic import BaseModel


class AdminOverview(BaseModel):
    """Global operational counts — no per-user PII, read-only."""

    users: int
    spaces: int
    projects: int
    materials: int
    quizzes: int
    quiz_attempts: int
    evidence_rows: int
    recommendations: int
