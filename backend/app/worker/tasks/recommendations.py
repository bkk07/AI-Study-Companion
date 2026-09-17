"""Recommendation recompute task — Blueprint §16 / §18 `generate_recommendation`.

Recomputed after mastery-affecting events (quiz completion, explain-back,
flashcard review), not on every page load. Best-effort: failures are
logged and swallowed by callers so evidence writes never break because
the recommender failed. Deterministic — same inputs, same winner.
"""

from __future__ import annotations

import os
import uuid

from app.services import dashboard_service, recommendation_service
from app.worker.celery_app import celery_app
from app.worker.tasks import get_task_session


@celery_app.task(name="generate_recommendation", bind=True, max_retries=2)
def generate_recommendation(self, user_id: str, project_id: str) -> str | None:
    """Rebuild signals and persist the current recommendation. Returns row id."""
    db = get_task_session()
    try:
        uid, pid = uuid.UUID(user_id), uuid.UUID(project_id)
        project = db.get(__import__("app.models.project", fromlist=["Project"]).Project, pid)
        goal_keywords = (
            recommendation_service.goal_keywords_for_project(project.name, project.goal)
            if project is not None
            else ()
        )
        _, signals = dashboard_service.build_dashboard(db, user_id=uid, project_id=pid)
        row = recommendation_service.recommend(
            db, user_id=uid, project_id=pid, signals=signals,
            goal_keywords=goal_keywords,
        )
        return str(row.id) if row is not None else None
    except (LookupError, ValueError):
        # Nothing scorable or scope vanished — not a retryable failure.
        return None
    finally:
        db.close()


def refresh_best_effort(user_id: uuid.UUID, project_id: uuid.UUID) -> None:
    """Fire-and-forget recompute; never raises into evidence-write paths.

    Skipped under pytest: with no broker in unit tests, `delay()` would
    block on connection retries and slow every evidence-writing test to a
    crawl before failing into the except below. Production always dispatches.
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        generate_recommendation.delay(str(user_id), str(project_id))
    except Exception:
        pass
