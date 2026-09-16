"""Page-level OCR via Tesseract — hybrid PDF pipeline branch (worker only).

Only invoked for pages where PyMuPDF finds no meaningful text but the page
carries image content (i.e. scanned pages). Normal text pages never reach
here, so OCR cost stays proportional to scanned pages, not documents.

pytesseract/Pillow are imported lazily so API/test processes without the
Tesseract system binary can still import this module — failures surface as
OcrError at call time, and the caller (extraction router) degrades the page
instead of failing the document.
"""

import logging

log = logging.getLogger(__name__)


class OcrError(Exception):
    """Raised when a page cannot be OCR'd (missing binary, bad image, ...)."""


def ocr_fitz_page(page, *, dpi: int = 300, language: str = "eng") -> str:
    """Render one PyMuPDF page to pixels and OCR it with Tesseract.

    Args:
        page: an open `fitz.Page` (caller owns the document lifetime).
        dpi: render resolution. 300 is Tesseract's well-established sweet
            spot — lower loses glyph detail, higher only adds cost.
        language: Tesseract language code(s), e.g. "eng" or "eng+deu".

    Returns:
        Raw OCR text (may be empty when nothing was recognized).

    Raises:
        OcrError: on any failure — missing binary, render error, etc.
    """
    try:
        import fitz
    except ImportError as e:
        raise OcrError(f"PyMuPDF is not available: {e}") from e
    try:
        from PIL import Image
    except ImportError as e:
        raise OcrError(f"Pillow is not available: {e}") from e
    try:
        import pytesseract
    except ImportError as e:
        raise OcrError(f"pytesseract is not available: {e}") from e

    try:
        zoom = max(dpi, 72) / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        if pix.n - pix.alpha > 3:  # CMYK etc. — Tesseract wants RGB/gray
            pix = fitz.Pixmap(fitz.csRGB, pix)
        import io

        png = pix.tobytes("png")
        image = Image.open(io.BytesIO(png))
    except Exception as e:
        raise OcrError(f"page render failed: {e}") from e

    try:
        return pytesseract.image_to_string(image, lang=language) or ""
    except Exception as e:
        raise OcrError(f"tesseract failed: {e}") from e
