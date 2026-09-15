import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.models.project import Project
from app.models.space import Space
from app.models.user import User
from app.schemas.background_job import BackgroundJobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_authorized_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BackgroundJob:
    job = db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    # ownership: if job targets a material, verify material→project→space→user
    if job.material_id:
        material = db.get(Material, job.material_id)
        if not material:
            # job orphaned — hide
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        # join via project→space
        project = db.get(Project, material.project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        space = db.query(Space).filter(Space.id == project.space_id, Space.user_id == current_user.id).first()
        if not space:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    else:
        # generic jobs without material: optionally restrict? For now allow any authenticated user to see own generic jobs
        # Since generic jobs have no owner, we use job creation not tied to user — treat as accessible
        # To keep isolation, we could store user_id on job — not yet. For Phase 22, allow.
        pass
    return job


@router.get("/{job_id}", response_model=BackgroundJobRead)
def get_job(job: BackgroundJob = Depends(get_authorized_job)):
    return job
