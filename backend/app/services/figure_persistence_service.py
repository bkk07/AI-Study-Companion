"""Figure persistence — PNG bytes → shared volume + material_figures rows.

Called once per extraction (worker only), best-effort: any failure is
reported, never raised into the extraction result. Re-runs replace a
material's figures (delete + insert, same idempotency as chunks), and image
files are overwritten at deterministic paths so retries never orphan rows.

Layout (sibling of the stored PDF, no new volume needed):
    {pdf_parent}/{pdf_stem}_figures/p{page}_{idx}.png (+ _thumb.png)
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.material_figure import FIGURE_TYPES, MaterialFigure

log = logging.getLogger(__name__)

THUMB_MAX_PX = 480


def figures_dir_for(storage_path: str) -> Path:
    """Deterministic sibling dir for a material's figures."""
    pdf = Path(storage_path)
    return pdf.parent / f"{pdf.stem}_figures"


def _write_png_and_thumb(fig_dir: Path, name: str, png_bytes: bytes) -> tuple[str, str | None]:
    """Write full PNG + small thumbnail. Returns (png_path, thumb_path|None)."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    png_path = fig_dir / f"{name}.png"
    png_path.write_bytes(png_bytes)
    thumb_path: str | None = None
    try:
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(png_bytes))
        image.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX))
        thumb = fig_dir / f"{name}_thumb.png"
        image.save(thumb, format="PNG")
        thumb_path = str(thumb)
    except Exception as e:
        log.warning("figure thumbnail failed %s: %s", name, str(e)[:200])
    return str(png_path), thumb_path


def collect_figures(pages: list[dict]) -> list[tuple[int, dict]]:
    """[(page_number, figure_record)] for records carrying PNG bytes."""
    out: list[tuple[int, dict]] = []
    for page in pages or []:
        try:
            number = int(page.get("page_number", 0))
        except (TypeError, ValueError):
            continue
        for fig in page.get("figures") or []:
            if isinstance(fig, dict) and fig.get("_png_bytes"):
                out.append((number, fig))
    return out


def save_figures(
    db: Session,
    *,
    project_id: uuid.UUID,
    material_id: uuid.UUID,
    storage_path: str,
    pages: list[dict],
    vision_model: str | None = None,
) -> dict:
    """Persist a material's figures: files + rows (replace semantics).

    Returns {"figures": n}. Raises on DB errors (caller decides: the
    extraction task treats this as best-effort and only records the error).
    """
    figs = collect_figures(pages)
    db.query(MaterialFigure).filter(MaterialFigure.material_id == material_id).delete(
        synchronize_session=False
    )
    if not figs:
        db.commit()
        return {"figures": 0}
    fig_dir = figures_dir_for(storage_path)
    try:
        from app.core.config import get_settings

        resolved_model = vision_model or (get_settings().nararouter_model or "").strip() or None
    except Exception:
        resolved_model = vision_model
    count = 0
    for page_number, fig in figs:
        try:
            idx = int(fig.get("index", 0) or 0)
        except (TypeError, ValueError):
            continue
        png = fig.pop("_png_bytes", None)
        if not png or idx <= 0:
            continue
        ftype = str(fig.get("figure_type") or "DIAGRAM").upper()
        if ftype not in FIGURE_TYPES:
            ftype = "DIAGRAM"
        name = f"p{page_number}_{idx}"
        try:
            png_path, thumb_path = _write_png_and_thumb(fig_dir, name, png)
        except Exception as e:
            log.warning("figure write failed p=%s idx=%s: %s", page_number, idx, str(e)[:200])
            continue
        db.add(
            MaterialFigure(
                project_id=project_id,
                material_id=material_id,
                page_number=page_number,
                fig_index=idx,
                figure_type=ftype,
                storage_path=png_path,
                thumb_path=thumb_path,
                image_hash=(fig.get("image_hash") or None),
                summary=(fig.get("summary") or fig.get("caption") or None),
                markdown_table=fig.get("markdown_table"),
                latex_table=fig.get("latex_table"),
                ocr_text=(fig.get("ocr_text") or None),
                vision_model=resolved_model,
            )
        )
        count += 1
    db.commit()
    return {"figures": count}
