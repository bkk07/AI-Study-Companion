import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.background_job import BackgroundJob

ALLOWED_STATUSES = {"pending", "running", "completed", "failed"}
# Allowed transitions: pending→running→completed/failed; also allow pending→failed directly for validation errors
ALLOWED_TRANSITIONS = {
    "pending": {"running", "failed"},
    "running": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
}


def create_job(
    db: Session,
    job_type: str,
    material_id: uuid.UUID | None = None,
    celery_task_id: str | None = None,
) -> BackgroundJob:
    if not job_type or not job_type.strip():
        raise ValueError("job_type required")
    job = BackgroundJob(
        job_type=job_type.strip(),
        status="pending",
        material_id=material_id,
        celery_task_id=celery_task_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: uuid.UUID) -> BackgroundJob | None:
    return db.get(BackgroundJob, job_id)


def _transition(db: Session, job: BackgroundJob, target: str, error: str | None = None) -> BackgroundJob:
    if target not in ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status {target}")
    if target not in ALLOWED_TRANSITIONS.get(job.status, set()) and job.status != target:
        # allow idempotent same-status, but not backwards
        if job.status != target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition {job.status}→{target}",
            )
    job.status = target
    if error is not None:
        job.error = error
    elif target != "failed":
        # clear error on non-failed unless explicitly set
        pass
    db.commit()
    db.refresh(job)
    return job


def mark_running(db: Session, job_id: uuid.UUID) -> BackgroundJob:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _transition(db, job, "running")


def mark_completed(db: Session, job_id: uuid.UUID) -> BackgroundJob:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _transition(db, job, "completed")


def mark_failed(db: Session, job_id: uuid.UUID, error: str) -> BackgroundJob:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not error or not error.strip():
        error = "Unknown error"
    return _transition(db, job, "failed", error=error.strip())
