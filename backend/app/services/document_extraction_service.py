"""Hybrid PDF extraction — PyMuPDF text with per-page Tesseract OCR routing.

Every page is routed independently:

    meaningful PyMuPDF text  → TEXT (images on the page are noted, not OCR'd)
    no meaningful text + page images → Tesseract OCR → OCR (or EMPTY on failure)
    no meaningful text + no images   → EMPTY (slot kept, no content invented)

TEXT and OCR pages merge into one normalized representation —
``{page_number, text, extraction_method, has_images, ocr_error}`` — so all
downstream stages (chunking, embeddings, structure, retrieval) work without
caring where the text came from. Traceability (document → page → chunk) is
preserved via page_number + extraction_method on every chunk.

Only genuinely unprocessable documents (corrupt, zero pages, or no usable
content on ANY page) raise ValueError; a single bad page — including an OCR
failure — never fails the document.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF — worker only, never on request path except via task

from app.core.config import get_settings
from app.services import ocr_service
from app.services.ocr_service import OcrError

log = logging.getLogger(__name__)

TEXT = "TEXT"
OCR = "OCR"
EMPTY = "EMPTY"

# Meaningfulness floor for PyMuPDF output. Below this a page is NOT trusted
# as real text when a rendered page image exists to OCR instead: such short
# extractions are typically running heads, folio numbers ("Page 3"), or
# vector-text fragments of an otherwise scanned page — never body content.
# The bar is deliberately low so genuine sparse pages (chapter titles) still
# count as TEXT when there is nothing to OCR; it only gates OCR routing.
MIN_MEANINGFUL_CHARS = 20
MIN_MEANINGFUL_WORDS = 3


def is_meaningful_text(text: str | None) -> bool:
    """True when extracted text is substantial enough to trust over OCR."""
    if not text or not text.strip():
        return False
    stripped = text.strip()
    return len(stripped) >= MIN_MEANINGFUL_CHARS and len(stripped.split()) >= MIN_MEANINGFUL_WORDS


def page_has_images(page: "fitz.Page") -> bool:
    """True when the page embeds image XObjects (scanned-page indicator)."""
    try:
        return bool(page.get_images(full=True))
    except Exception:
        return False


def _route_page(
    page: "fitz.Page",
    page_number: int,
    *,
    ocr_enabled: bool,
    dpi: int,
    language: str,
) -> dict:
    """Route one page → normalized record (never raises for page problems)."""
    try:
        raw = page.get_text() or ""
    except Exception:
        raw = ""
    sparse = raw.strip()
    try:
        has_images = page_has_images(page)
    except Exception:
        has_images = False

    if is_meaningful_text(sparse):
        # Text + diagram pages land here: real text wins, no automatic OCR.
        log.info("page routed: page=%s extraction_method=%s", page_number, TEXT)
        return {
            "page_number": page_number,
            "text": sparse,
            "extraction_method": TEXT,
            "has_images": has_images,
            "ocr_error": None,
        }

    if has_images and ocr_enabled:
        log.info("page=%s event=ocr_started", page_number)
        try:
            ocr_text = ocr_service.ocr_fitz_page(page, dpi=dpi, language=language)
        except OcrError as e:
            msg = str(e)[:500]
            log.warning("page=%s event=ocr_failed error=%s", page_number, msg)
            return {
                "page_number": page_number,
                "text": sparse,  # keep whatever was extracted; invent nothing
                "extraction_method": EMPTY,
                "has_images": True,
                "ocr_error": msg,
            }
        log.info("page=%s event=ocr_completed", page_number)
        if is_meaningful_text(ocr_text):
            log.info("page routed: page=%s extraction_method=%s", page_number, OCR)
            return {
                "page_number": page_number,
                "text": ocr_text.strip(),
                "extraction_method": OCR,
                "has_images": True,
                "ocr_error": None,
            }
        log.warning("page=%s event=ocr_empty", page_number)
        return {
            "page_number": page_number,
            "text": sparse,
            "extraction_method": EMPTY,
            "has_images": True,
            "ocr_error": "ocr produced no meaningful text",
        }

    ocr_error = None
    if has_images and not ocr_enabled:
        ocr_error = "ocr disabled by OCR_ENABLED=false"
    log.info("page routed: page=%s extraction_method=%s", page_number, EMPTY)
    return {
        "page_number": page_number,
        "text": sparse,
        "extraction_method": EMPTY,
        "has_images": has_images,
        "ocr_error": ocr_error,
    }


def _route_open_doc(doc: "fitz.Document", *, ocr_enabled: bool, dpi: int, language: str) -> list[dict]:
    """Route every page of an open document (slot per page, numbering kept)."""
    pages: list[dict] = []
    for i in range(doc.page_count):
        try:
            record = _route_page(
                doc[i], i + 1, ocr_enabled=ocr_enabled, dpi=dpi, language=language
            )
        except Exception as e:  # a single page must never kill the document
            log.warning("page=%s event=route_failed error=%s", i + 1, str(e)[:200])
            record = {
                "page_number": i + 1,
                "text": "",
                "extraction_method": EMPTY,
                "has_images": False,
                "ocr_error": f"routing failed: {e}"[:500],
            }
        pages.append(record)
    return pages


def _resolve_ocr_options(
    ocr_enabled: bool | None, dpi: int | None, language: str | None
) -> tuple[bool, int, str]:
    settings = get_settings()
    return (
        settings.ocr_enabled if ocr_enabled is None else ocr_enabled,
        settings.ocr_dpi if dpi is None else dpi,
        settings.ocr_language if language is None else language,
    )


def _open_pdf(storage_path: str) -> "fitz.Document":
    """Open a PDF or raise FileNotFoundError/ValueError (unchanged semantics)."""
    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {storage_path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {storage_path}")
    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF: {e}") from e
    if doc.page_count == 0:
        doc.close()
        raise ValueError("PDF has no pages")
    return doc


def extract_document_pages(
    storage_path: str,
    *,
    ocr_enabled: bool | None = None,
    dpi: int | None = None,
    language: str | None = None,
) -> list[dict]:
    """Per-page routed extraction: [{page_number, text, extraction_method,
    has_images, ocr_error}]. Never raises for page-level problems."""
    enabled, resolved_dpi, resolved_lang = _resolve_ocr_options(ocr_enabled, dpi, language)
    doc = _open_pdf(storage_path)
    try:
        return _route_open_doc(doc, ocr_enabled=enabled, dpi=resolved_dpi, language=resolved_lang)
    finally:
        doc.close()


def combine_page_texts(pages: list[dict]) -> str:
    """Join per-page texts with page-boundary separators (citation/chunking)."""
    return "\n\n".join(p["text"] for p in pages if (p.get("text") or "").strip())


def no_content_error(pages: list[dict]) -> ValueError:
    """Diagnosable error for documents with no usable content on any page."""
    ocr_failures = [p for p in pages if p.get("ocr_error")]
    msg = "PDF contains no extractable text"
    if ocr_failures:
        first = (ocr_failures[0].get("ocr_error") or "")[:200]
        msg += f"; OCR failed on {len(ocr_failures)} page(s) (e.g. {first})"
    return ValueError(msg)


def extract_pdf_text(
    storage_path: str,
    *,
    ocr_enabled: bool | None = None,
    dpi: int | None = None,
    language: str | None = None,
) -> tuple[str, int]:
    """Extract full text via per-page routing (PyMuPDF + OCR for scans).

    Returns (full_text, page_count). Uploaded content is untrusted data —
    text is returned as-is, never executed or interpreted as instructions.

    Raises:
        FileNotFoundError: if path does not exist
        ValueError: if file is not a valid PDF, has no pages, or no page
            yielded usable content (genuinely empty OR every OCR attempt failed)
    """
    pages = extract_document_pages(
        storage_path, ocr_enabled=ocr_enabled, dpi=dpi, language=language
    )
    full_text = combine_page_texts(pages)
    if not full_text.strip():
        raise no_content_error(pages)
    return full_text, len(pages)


def extract_pages(
    storage_path: str,
    *,
    ocr_enabled: bool | None = None,
    dpi: int | None = None,
    language: str | None = None,
) -> list[dict]:
    """Per-page routed texts: [{page_number, text, extraction_method,
    has_images, ocr_error}]. The page_number/text keys keep every existing
    caller working; routing metadata rides along for chunking/traceability.
    """
    return extract_document_pages(
        storage_path, ocr_enabled=ocr_enabled, dpi=dpi, language=language
    )
