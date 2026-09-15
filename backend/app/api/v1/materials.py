import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import get_authorized_project
from app.models.material import Material
from app.models.project import Project
from app.schemas.material import MaterialRead
from app.services import storage_service
from app.services.storage_service import save_pdf

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
    db.commit()
    db.refresh(material)
    return material


@router.get("", response_model=list[MaterialRead])
def list_materials(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    return db.query(Material).filter(Material.project_id == project.id).order_by(Material.created_at.asc()).all()
