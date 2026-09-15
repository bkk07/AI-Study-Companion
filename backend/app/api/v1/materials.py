import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import get_authorized_project
from app.models.material import Material
from app.models.project import Project
from app.schemas.material import MaterialRead
from app.services import job_service, storage_service
from app.services.storage_service import save_pdf
from app.worker.tasks.extraction import process_pdf

router = APIRouter(prefix="/projects/{project_id}/materials", tags=["materials"])


@router.post("", response_model=MaterialRead, status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    storage_path, filename = await save_pdf(project.id, file)
    material = Material(project_id=project.id, filename=filename, storage_path=storage_path, status="pending")
    db.add(material)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Avoid orphan files when the material row fails to persist
        try:
            Path(storage_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise
    db.refresh(material)
    # Phase 23: create extraction job + dispatch Celery (best-effort, never blocks upload)
    job = job_service.create_job(db, job_type="process_pdf", material_id=material.id)
    try:
        result = process_pdf.delay(str(job.id), str(material.id))
        job.celery_task_id = result.id
        db.commit()
        db.refresh(job)
    except Exception as e:
        # Broker down — leave job pending with error hint, upload still succeeds
        try:
            job_service.mark_failed(db, job.id, f"Dispatch failed: {e}"[:1000])
        except Exception:
            pass
    db.refresh(material)
    return material


@router.get("", response_model=list[MaterialRead])
def list_materials(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    return db.query(Material).filter(Material.project_id == project.id).order_by(Material.created_at.asc()).all()
