from pathlib import Path

import fitz  # PyMuPDF — worker only, never on request path except via task


def extract_pdf_text(storage_path: str) -> tuple[str, int]:
    """
    Extract raw text from PDF at storage_path using PyMuPDF.

    Returns (full_text, page_count). Per-page texts are joined with double
    newlines to preserve page boundaries for later citation/chunking.

    Uploaded content is untrusted data — text is returned as-is, never
    executed or interpreted as instructions.

    Raises:
        FileNotFoundError: if path does not exist
        ValueError: if file is not a valid PDF or has no readable pages
    """
    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {storage_path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {storage_path}")

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF: {e}") from e

    try:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")
        pages: list[str] = []
        for i in range(doc.page_count):
            try:
                page = doc[i]
                text = page.get_text() or ""
            except Exception:
                text = ""
            # Keep page slot even if empty to preserve page_number mapping
            pages.append(text.strip())
        full_text = "\n\n".join(p for p in pages if p)
        if not full_text.strip():
            raise ValueError("PDF contains no extractable text")
        return full_text, doc.page_count
    finally:
        doc.close()


def extract_pages(storage_path: str) -> list[dict]:
    """
    Return per-page texts for citation support: [{page_number, text}].
    """
    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {storage_path}")
    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF: {e}") from e
    try:
        result = []
        for i in range(doc.page_count):
            try:
                text = doc[i].get_text() or ""
            except Exception:
                text = ""
            result.append({"page_number": i + 1, "text": text.strip()})
        return result
    finally:
        doc.close()
