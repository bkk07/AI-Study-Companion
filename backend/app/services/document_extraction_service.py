"""Full PDF extraction — PyMuPDF text + tables + figure captions + OCR routing.

Every page is routed independently:

    meaningful PyMuPDF text  → TEXT (+ structured tables + figure captions)
    no meaningful text + page images → Tesseract OCR → OCR (or EMPTY on failure)
    no meaningful text + no images   → EMPTY (slot kept, no content invented)

TEXT and OCR pages merge into one normalized representation —
``{page_number, text, extraction_method, has_images, ocr_error,
tables_count, figures}`` — so all downstream stages (chunking, embeddings,
structure, retrieval) work without caring where the text came from.
Traceability (document → page → chunk) is preserved via page_number +
extraction_method on every chunk.

Tables use PyMuPDF ``find_tables`` (no new deps) and are appended as
GitHub-Flavored Markdown so LLMs/RAG see row/column structure. Figures on
TEXT pages are cropped, classified, and described via NaraRouter vision
(chart → Markdown data table, table scan → LaTeX tabular, photo/diagram →
summary); any vision failure falls back to cropped-OCR/placeholder — never
failing the document. Scanned (OCR) pages skip figure captioning to avoid
double processing the full-page scan.

Only genuinely unprocessable documents (corrupt, zero pages, or no usable
content on ANY page) raise ValueError; a single bad page — including an OCR
or vision failure — never fails the document.
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

# Full-extraction budgets — bound cost/time on image/table-heavy PDFs.
MAX_TABLES_PER_PAGE = 3
MAX_TABLE_ROWS = 30
MAX_TABLE_COLS = 10
MAX_CELL_CHARS = 300
MAX_FIGURES_PER_PAGE = 4
MIN_FIG_WIDTH = 40
MIN_FIG_HEIGHT = 40


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


# ---------------------------------------------------------------- tables ---


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip().replace("\n", " ").replace("\r", " ")
    s = " ".join(s.split())  # collapse whitespace
    s = s.replace("|", "/")  # keep GFM table intact
    return s[:MAX_CELL_CHARS]


def _table_to_markdown(rows: list[list]) -> str:
    """Normalize find_tables output to GFM markdown (header + separator)."""
    cleaned: list[list[str]] = []
    for r in (rows or [])[:MAX_TABLE_ROWS]:
        cells = [_clean_cell(c) for c in (r or [])[:MAX_TABLE_COLS]]
        if any(cells):
            cleaned.append(cells)
    if not cleaned:
        return ""
    width = max(len(r) for r in cleaned)
    cleaned = [r + [""] * (width - len(r)) for r in cleaned]
    header = cleaned[0]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for r in cleaned[1:]:
        lines.append("| " + " | ".join(r) + " |")
    if len(cleaned) == 1:  # single-row table: still valid GFM with separator
        pass
    return "\n".join(lines)


def _extract_tables_markdown(page: "fitz.Page") -> list[str]:
    """Structured tables on one page → list of markdown strings (best-effort)."""
    try:
        finder = page.find_tables()
    except Exception as e:
        log.warning("table detection failed: %s", str(e)[:200])
        return []
    out: list[str] = []
    try:
        tables = list(finder)
    except Exception:
        return []
    for t in tables[:MAX_TABLES_PER_PAGE]:
        try:
            md = _table_to_markdown(t.extract())
        except Exception:
            continue
        if md.strip():
            out.append(md[:8000])  # cap pathological tables
    return out


# --------------------------------------------------------------- figures ---


def _figure_candidates(page: "fitz.Page") -> list[tuple[int, "fitz.Rect"]]:
    """Deduped (xref, largest-rect) figure candidates, biggest first."""
    try:
        images = page.get_images(full=True)
    except Exception:
        return []
    seen: set[int] = set()
    cands: list[tuple[int, "fitz.Rect"]] = []
    for im in images:
        try:
            xref = int(im[0])
        except Exception:
            continue
        if xref in seen or xref <= 0:
            continue
        seen.add(xref)
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            continue
        best = None
        best_area = 0.0
        for r in rects or []:
            try:
                if r.width < MIN_FIG_WIDTH or r.height < MIN_FIG_HEIGHT:
                    continue
                area = r.width * r.height
                if area > best_area:
                    best_area = area
                    best = r
            except Exception:
                continue
        if best is not None:
            cands.append((xref, best))
    cands.sort(key=lambda c: c[1].width * c[1].height, reverse=True)
    return cands[:MAX_FIGURES_PER_PAGE]


def _render_figure_png(page: "fitz.Page", rect: "fitz.Rect") -> bytes | None:
    """Render one figure rect to PNG bytes (~150 DPI, best-effort)."""
    try:
        clip = fitz.Rect(rect) & page.rect
        if clip.is_empty or clip.width < MIN_FIG_WIDTH or clip.height < MIN_FIG_HEIGHT:
            return None
        zoom = 150.0 / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        if pix.n - pix.alpha > 3:  # CMYK etc. → RGB for vision/OCR
            pix = fitz.Pixmap(fitz.csRGB, pix)
        return pix.tobytes("png")
    except Exception as e:
        log.warning("figure render failed: %s", str(e)[:200])
        return None


def _ocr_crop_fallback(png_bytes: bytes, language: str) -> str:
    """OCR a cropped figure directly (NOT via ocr_service seam — that seam is
    reserved for full-page scan routing and is asserted untouched in tests)."""
    try:
        import io

        from PIL import Image

        import pytesseract

        image = Image.open(io.BytesIO(png_bytes))
        return (pytesseract.image_to_string(image, lang=language) or "").strip()
    except Exception:
        return ""


_LATEX_SPECIALS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def _latex_cell(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip().replace("\n", " ").replace("\r", " ")
    s = " ".join(s.split())
    return "".join(_LATEX_SPECIALS.get(ch, ch) for ch in s)[:MAX_CELL_CHARS]


def table_rows_to_latex(rows: list[list]) -> str:
    """Vector-table rows → LaTeX tabular (render-exact twin of the markdown)."""
    cleaned: list[list[str]] = []
    for r in (rows or [])[:MAX_TABLE_ROWS]:
        cells = [_latex_cell(c) for c in (r or [])[:MAX_TABLE_COLS]]
        if any(cells):
            cleaned.append(cells)
    if not cleaned:
        return ""
    width = max(len(r) for r in cleaned)
    cleaned = [r + [""] * (width - len(r)) for r in cleaned]
    colspec = "|" + "|".join(["l"] * width) + "|"
    lines = [f"\\begin{{tabular}}{{{colspec}}}", "\\hline"]
    for i, r in enumerate(cleaned):
        lines.append(" & ".join(r) + r" \\ \hline")
        if i == 0:
            pass  # header row kept bold-free; structure is what matters
    lines.append("\\end{tabular}")
    return "\n".join(lines)[:8000]


def _extract_tables_full(page: "fitz.Page") -> tuple[list[str], list[str]]:
    """Vector tables on one page → (markdown list, latex list), best-effort."""
    try:
        finder = page.find_tables()
    except Exception as e:
        log.warning("table detection failed: %s", str(e)[:200])
        return [], []
    try:
        tables = list(finder)
    except Exception:
        return [], []
    md_out: list[str] = []
    latex_out: list[str] = []
    for t in tables[:MAX_TABLES_PER_PAGE]:
        try:
            rows = t.extract()
        except Exception:
            continue
        md = _table_to_markdown(rows)
        if md.strip():
            md_out.append(md[:8000])
            latex = table_rows_to_latex(rows)
            if latex.strip():
                latex_out.append(latex)
    return md_out, latex_out


def _extract_tables_markdown(page: "fitz.Page") -> list[str]:
    """Structured tables on one page → list of markdown strings (best-effort)."""
    md, _ = _extract_tables_full(page)
    return md


def _image_hash(png_bytes: bytes) -> str:
    try:
        import hashlib

        return hashlib.sha256(png_bytes).hexdigest()[:16]
    except Exception:
        return ""


def _caption_figures(
    page: "fitz.Page",
    page_number: int,
    language: str,
    budget: dict,
) -> list[dict]:
    """Caption + classify figure candidates on a TEXT page. Never raises;
    consumes budget['remaining'] (global per-doc cap). Returns rich records::

        {index, caption, figure_type, summary, markdown_table, latex_table,
         ocr_text, image_hash, _png_bytes}

    ``_png_bytes`` is transient (popped by the persistence layer); everything
    else is JSON-safe and rides into chunks/RAG. DECORATIVE crops are dropped.
    """
    if budget.get("remaining", 0) <= 0:
        return []
    out: list[dict] = []
    try:
        from app.services import vision_service
    except Exception:
        vision_service = None  # type: ignore
    for idx, (_xref, rect) in enumerate(_figure_candidates(page), start=1):
        if budget["remaining"] <= 0:
            break
        budget["remaining"] -= 1
        png = _render_figure_png(page, rect)
        if not png:
            continue
        record: dict = {
            "index": idx,
            "caption": "",
            "figure_type": "DIAGRAM",
            "summary": "",
            "markdown_table": None,
            "latex_table": None,
            "ocr_text": "",
            "image_hash": _image_hash(png),
            "_png_bytes": png,
        }
        analysis: dict | None = None
        if vision_service is not None:
            try:
                analysis = vision_service.analyze_figure_bytes(
                    png, page_number=page_number, fig_index=idx
                )
            except Exception:
                analysis = None
        if analysis:
            ftype = str(analysis.get("figure_type") or "DIAGRAM").upper()
            if ftype == "DECORATIVE":
                log.info("page=%s fig=%s event=figure_decorative_skipped", page_number, idx)
                continue
            record["figure_type"] = ftype
            record["summary"] = str(analysis.get("summary") or "")[:1500]
            record["markdown_table"] = analysis.get("markdown_table")
            record["latex_table"] = analysis.get("latex_table")
            record["caption"] = record["summary"] or f"{ftype.lower()} on page {page_number}"
            out.append(record)
            continue
        # Vision unavailable/failed → legacy caption path, then cropped OCR.
        caption: str | None = None
        if vision_service is not None:
            try:
                caption = vision_service.caption_image_bytes(
                    png, page_number=page_number, fig_index=idx
                )
            except Exception:
                caption = None
        if caption and caption.strip():
            record["caption"] = caption.strip()[:1500]
            record["summary"] = record["caption"]
            out.append(record)
            continue
        ocr_text = _ocr_crop_fallback(png, language)
        if is_meaningful_text(ocr_text):
            record["ocr_text"] = ocr_text[:500]
            record["caption"] = f"Figure contains text: {ocr_text[:500]}"
            record["summary"] = record["caption"]
        else:
            record["caption"] = "image/diagram (visual details not transcribed)"
            record["summary"] = record["caption"]
        out.append(record)
    return out


def _figure_text_block(f: dict, page_number: int) -> str:
    """One figure → citable text block (chart→MD, table-scan→LaTeX)."""
    idx = f.get("index", 0)
    ftype = str(f.get("figure_type") or "DIAGRAM").upper()
    caption = (f.get("caption") or f.get("summary") or "").strip()
    head = f"[Figure p{page_number}.{idx} ({ftype.lower()}): {caption}]"
    if ftype == "CHART" and f.get("markdown_table"):
        return f"{head}\n{f['markdown_table']}"
    if ftype == "TABLE_SCAN" and f.get("latex_table"):
        return f"{head}\n```latex\n{f['latex_table']}\n```"
    return head


def _enrich_text(
    base: str, tables: list[str], figures: list[dict], page_number: int
) -> str:
    """Append table markdown + typed figure blocks to page text (searchable)."""
    parts = [base]
    for i, md in enumerate(tables, start=1):
        parts.append(f"\n\n[Table p{page_number}.{i}]\n{md}")
    for f in figures:
        parts.append("\n\n" + _figure_text_block(f, page_number))
    return "".join(parts) if len(parts) == 1 else "\n".join(p for p in parts if p)


# ---------------------------------------------------------------- routing ---


def _route_page(
    page: "fitz.Page",
    page_number: int,
    *,
    ocr_enabled: bool,
    dpi: int,
    language: str,
    tables_enabled: bool = True,
    vision_budget: dict | None = None,
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
        # Text (+tables/diagrams) pages: enrich, no full-page OCR.
        tables: list[str] = []
        figures: list[dict] = []
        try:
            if tables_enabled:
                tables = _extract_tables_markdown(page)
        except Exception as e:
            log.warning("page=%s event=tables_failed error=%s", page_number, str(e)[:200])
        try:
            if has_images and vision_budget is not None and vision_budget.get("remaining", 0) > 0:
                figures = _caption_figures(page, page_number, language, vision_budget)
        except Exception as e:
            log.warning("page=%s event=figures_failed error=%s", page_number, str(e)[:200])
            figures = []
        text = _enrich_text(sparse, tables, figures, page_number)
        log.info(
            "page routed: page=%s extraction_method=%s tables=%s figures=%s",
            page_number,
            TEXT,
            len(tables),
            len(figures),
        )
        return {
            "page_number": page_number,
            "text": text,
            "extraction_method": TEXT,
            "has_images": has_images,
            "ocr_error": None,
            "tables_count": len(tables),
            "tables_markdown": tables,
            "figures": figures,
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
                "tables_count": 0,
                "tables_markdown": [],
                "figures": [],
            }
        log.info("page=%s event=ocr_completed", page_number)
        if is_meaningful_text(ocr_text):
            log.info("page routed: page=%s extraction_method=%s", page_number, OCR)
            # OCR pages skip figure captioning (the full-page render IS the
            # figure); tables agresti from scans are out of scope for v1.
            return {
                "page_number": page_number,
                "text": ocr_text.strip(),
                "extraction_method": OCR,
                "has_images": True,
                "ocr_error": None,
                "tables_count": 0,
                "tables_markdown": [],
                "figures": [],
            }
        log.warning("page=%s event=ocr_empty", page_number)
        return {
            "page_number": page_number,
            "text": sparse,
            "extraction_method": EMPTY,
            "has_images": True,
            "ocr_error": "ocr produced no meaningful text",
            "tables_count": 0,
            "tables_markdown": [],
            "figures": [],
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
        "tables_count": 0,
        "tables_markdown": [],
        "figures": [],
    }


def _resolve_full_options(
    ocr_enabled: bool | None,
    dpi: int | None,
    language: str | None,
    tables_enabled: bool | None = None,
    vision_enabled: bool | None = None,
) -> tuple[bool, int, str, bool, bool, int]:
    settings = get_settings()
    return (
        settings.ocr_enabled if ocr_enabled is None else ocr_enabled,
        settings.ocr_dpi if dpi is None else dpi,
        settings.ocr_language if language is None else language,
        settings.tables_enabled if tables_enabled is None else tables_enabled,
        settings.vision_enabled if vision_enabled is None else vision_enabled,
        int(getattr(settings, "vision_max_images_per_doc", 12) or 12),
    )


def _route_open_doc(
    doc: "fitz.Document",
    *,
    ocr_enabled: bool,
    dpi: int,
    language: str,
    tables_enabled: bool = True,
    vision_enabled: bool = True,
    vision_budget: int = 12,
) -> list[dict]:
    """Route every page of an open document (slot per page, numbering kept)."""
    budget = {"remaining": vision_budget if vision_enabled else 0}
    pages: list[dict] = []
    for i in range(doc.page_count):
        try:
            record = _route_page(
                doc[i],
                i + 1,
                ocr_enabled=ocr_enabled,
                dpi=dpi,
                language=language,
                tables_enabled=tables_enabled,
                vision_budget=budget,
            )
        except Exception as e:  # a single page must never kill the document
            log.warning("page=%s event=route_failed error=%s", i + 1, str(e)[:200])
            record = {
                "page_number": i + 1,
                "text": "",
                "extraction_method": EMPTY,
                "has_images": False,
                "ocr_error": f"routing failed: {e}"[:500],
                "tables_count": 0,
                "tables_markdown": [],
                "figures": [],
            }
        pages.append(record)
    return pages


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
    tables_enabled: bool | None = None,
    vision_enabled: bool | None = None,
) -> list[dict]:
    """Per-page routed extraction: [{page_number, text, extraction_method,
    has_images, ocr_error, tables_count, tables_markdown, figures}].
    Never raises for page-level problems."""
    enabled, resolved_dpi, resolved_lang, tables_on, vision_on, budget = _resolve_full_options(
        ocr_enabled, dpi, language, tables_enabled, vision_enabled
    )
    doc = _open_pdf(storage_path)
    try:
        return _route_open_doc(
            doc,
            ocr_enabled=enabled,
            dpi=resolved_dpi,
            language=resolved_lang,
            tables_enabled=tables_on,
            vision_enabled=vision_on,
            vision_budget=budget,
        )
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
    tables_enabled: bool | None = None,
    vision_enabled: bool | None = None,
) -> tuple[str, int]:
    """Extract full text via per-page routing (text + tables + figures + OCR).

    Returns (full_text, page_count). Uploaded content is untrusted data —
    text is returned as-is, never executed or interpreted as instructions.

    Raises:
        FileNotFoundError: if path does not exist
        ValueError: if file is not a valid PDF, has no pages, or no page
            yielded usable content (genuinely empty OR every OCR attempt failed)
    """
    pages = extract_document_pages(
        storage_path,
        ocr_enabled=ocr_enabled,
        dpi=dpi,
        language=language,
        tables_enabled=tables_enabled,
        vision_enabled=vision_enabled,
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
    tables_enabled: bool | None = None,
    vision_enabled: bool | None = None,
) -> list[dict]:
    """Per-page routed texts: [{page_number, text, extraction_method,
    has_images, ocr_error, tables_count, figures}]. The page_number/text keys
    keep every existing caller working; routing + full-extraction metadata
    rides along for chunking/traceability.
    """
    return extract_document_pages(
        storage_path,
        ocr_enabled=ocr_enabled,
        dpi=dpi,
        language=language,
        tables_enabled=tables_enabled,
        vision_enabled=vision_enabled,
    )
