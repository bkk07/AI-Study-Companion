import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_project
from app.models.background_job import BackgroundJob
from app.models.material import Material
from app.models.project import Project
from app.models.user import User
from app.schemas.material import EnrichmentStatus, MaterialRead
from app.services import activity_service, job_service, storage_service
from app.services.storage_service import save_pdf
from app.worker.tasks.extraction import process_pdf

router = APIRouter(prefix="/projects/{project_id}/materials", tags=["materials"])

# Downstream stages that must finish before a material is truly "Ready"
# for the user (concepts/knowledge map). While any of these jobs for a
# material is still pending/running, the list endpoint reports the
# material as `processing` even though `materials.status` in DB is
# already `ready` (extraction done). Extraction failures stay `failed`.
DOWNSTREAM_JOB_TYPES = ("generate_embeddings", "build_structure")
ACTIVE_JOB_STATUSES = ("pending", "running")


@router.post("", response_model=MaterialRead, status_code=201)
async def upload_material(
    response: Response,
    file: UploadFile = File(...),
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
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
    dispatch_failed = False
    try:
        result = process_pdf.delay(str(job.id), str(material.id))
        job.celery_task_id = result.id
        db.commit()
        db.refresh(job)
    except Exception as e:
        # Broker down — the file is saved but nothing will ever process it.
        # Say so explicitly: 202 + material `failed` (with error_message the
        # UI already renders) instead of a misleading 201 `pending`.
        dispatch_failed = True
        try:
            job_service.mark_failed(db, job.id, f"Dispatch failed: {e}"[:1000])
        except Exception:
            pass
        material.status = "failed"
        material.error_message = (
            "Processing dispatch failed (job broker unavailable) — "
            "the file is saved but will not be processed. Re-upload to retry."
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
    db.refresh(material)
    if dispatch_failed:
        response.status_code = 202
    # §12: material.uploaded — idempotent on retry.
    activity_service.record_event_committed(
        db,
        user_id=current_user.id,
        project_id=project.id,
        space_id=project.space_id,
        event_type=activity_service.EVENT_MATERIAL_UPLOADED,
        entity_type="material",
        entity_id=material.id,
        payload={"filename": material.filename[:120]},
        idempotency_key=f"material:{material.id}:uploaded",
    )
    return material


@router.get("", response_model=list[MaterialRead])
def list_materials(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    materials = db.query(Material).filter(Material.project_id == project.id).order_by(Material.created_at.asc()).all()
    if not materials:
        return []
    # If extraction is done (ready) but embeddings/structure are still
    # queued/running, report `processing` so the UI does not show `Ready`
    # before concepts exist. Never downgrade `failed`.
    mat_ids = [m.id for m in materials]
    active_ids: set = set()
    # Latest downstream job status per (material, job_type) — drives the
    # `enrichment` field so the UI can show per-stage progress. Newest row
    # wins (a stage is queued exactly once per material today; newest-first
    # keeps this correct if that ever changes).
    latest: dict = {}
    try:
        rows = (
            db.query(BackgroundJob.material_id, BackgroundJob.job_type, BackgroundJob.status)
            .filter(
                BackgroundJob.material_id.in_(mat_ids),
                BackgroundJob.job_type.in_(DOWNSTREAM_JOB_TYPES),
            )
            .order_by(BackgroundJob.created_at.desc())
            .all()
        )
        for mat_id, job_type, status in rows:
            latest.setdefault((mat_id, job_type), status)
        active_ids = {
            mat_id
            for (mat_id, _), status in latest.items()
            if status in ACTIVE_JOB_STATUSES
        }
    except Exception:
        active_ids = set()
        latest = {}
    result: list[MaterialRead] = []
    for m in materials:
        data = MaterialRead.model_validate(m)
        data.enrichment = EnrichmentStatus(
            extraction=m.status,
            embeddings=latest.get((m.id, "generate_embeddings")),
            structure=latest.get((m.id, "build_structure")),
        )
        if m.status == "ready" and m.id in active_ids:
            result.append(data.model_copy(update={"status": "processing"}))
        else:
            result.append(data)
    return result
