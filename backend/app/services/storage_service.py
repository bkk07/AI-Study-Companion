import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


def _sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "document.pdf"
    # strip path components, keep basename only
    name = Path(filename).name.strip()
    if not name:
        return "document.pdf"
    return name


async def save_pdf(project_id: uuid.UUID, upload: UploadFile) -> tuple[str, str]:
    """
    Validate PDF (type + magic + size) and save to UPLOAD_DIR/{project_id}/{uuid}.pdf.
    Returns (storage_path, sanitized_filename).
    """
    filename = _sanitize_filename(upload.filename)
    # extension check — must be .pdf
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed (filename must end with .pdf)")

    # content_type check if client sent one (some clients send octet-stream, we still require magic)
    if upload.content_type and upload.content_type not in ALLOWED_CONTENT_TYPES:
        # allow octet-stream only if magic passes? strict: reject non-pdf content_type
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed (invalid content type)")

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File too large (max 10MB)")

    # Magic bytes %PDF
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed (invalid PDF header)")

    settings = get_settings()
    base = Path(settings.upload_dir)
    project_dir = base / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.pdf"
    storage_path = project_dir / stored_name
    # Prevent path traversal — storage_path is fully server-controlled
    storage_path.write_bytes(content)

    return str(storage_path), filename
