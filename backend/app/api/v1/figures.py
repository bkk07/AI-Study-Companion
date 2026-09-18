import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.authorization import get_authorized_project
from app.models.material import Material
from app.models.material_figure import MaterialFigure
from app.models.project import Project
from app.schemas.figure import FigureListResponse, FigureRead

router = APIRouter(tags=["figures"])


def _figure_image_url(project_id: uuid.UUID, material_id: uuid.UUID, figure_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/materials/{material_id}/figures/{figure_id}/image"


def _get_figure_or_404(
    db: Session, project: Project, material_id: uuid.UUID, figure_id: uuid.UUID
) -> MaterialFigure:
    material = (
        db.query(Material)
        .filter(Material.id == material_id, Material.project_id == project.id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    figure = (
        db.query(MaterialFigure)
        .filter(MaterialFigure.id == figure_id, MaterialFigure.material_id == material_id)
        .first()
    )
    if not figure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found")
    return figure


@router.get(
    "/projects/{project_id}/materials/{material_id}/figures",
    response_model=FigureListResponse,
)
def list_figures(
    project_id: uuid.UUID,
    material_id: uuid.UUID,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    if str(project.id) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    material = (
        db.query(Material)
        .filter(Material.id == material_id, Material.project_id == project.id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    rows = (
        db.query(MaterialFigure)
        .filter(MaterialFigure.material_id == material_id)
        .order_by(MaterialFigure.page_number.asc(), MaterialFigure.fig_index.asc())
        .all()
    )
    return FigureListResponse(
        material_id=material_id,
        figures=[
            FigureRead(
                id=r.id,
                material_id=r.material_id,
                page_number=r.page_number,
                fig_index=r.fig_index,
                figure_type=r.figure_type or "DIAGRAM",
                summary=r.summary,
                markdown_table=r.markdown_table,
                latex_table=r.latex_table,
                image_url=_figure_image_url(project.id, material_id, r.id),
                created_at=r.created_at,
            )
            for r in rows
        ],
    )


@router.get("/projects/{project_id}/materials/{material_id}/figures/{figure_id}/image")
def get_figure_image(
    project_id: uuid.UUID,
    material_id: uuid.UUID,
    figure_id: uuid.UUID,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    if str(project.id) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    figure = _get_figure_or_404(db, project, material_id, figure_id)
    # Contain the resolved path inside UPLOAD_DIR (stored paths are
    # server-generated, this is defense in depth).
    try:
        base = Path(get_settings().upload_dir).resolve()
        target = Path(figure.storage_path).resolve()
        if base not in target.parents and target != base:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found")
        if not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found")
    return FileResponse(str(target), media_type="image/png")
