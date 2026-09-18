"""Figure pipeline tests — typed vision output, LaTeX twin, text blocks.

Vision network is never touched: analyze/caption entry points return None
under pytest (PYTEST_CURRENT_TEST guard), so these tests exercise parsing,
builders, and the OCR/placeholder fallback path only.
"""

import os
import tempfile
from unittest.mock import patch

import fitz

from app.services import vision_service
from app.services.document_extraction_service import (
    _enrich_text,
    _figure_text_block,
    extract_document_pages,
    table_rows_to_latex,
)


def test_parse_analysis_json_fences_and_bare():
    fenced = '```json\n{"figure_type": "CHART", "summary": "s"}\n```'
    assert vision_service._parse_analysis_json(fenced) == {"figure_type": "CHART", "summary": "s"}
    assert vision_service._parse_analysis_json('noise {"figure_type": "PHOTO"} tail') == {
        "figure_type": "PHOTO"
    }
    assert vision_service._parse_analysis_json("not json at all") is None
    assert vision_service._parse_analysis_json("") is None


def test_figure_analysis_coercion():
    a = vision_service.FigureAnalysis.model_validate(
        {"figure_type": "chart", "summary": "  Bars up. ", "markdown_table": "| a |\n|---|"}
    )
    assert a.figure_type == "CHART"
    assert a.summary == "Bars up."
    assert a.latex_table is None
    weird = vision_service.FigureAnalysis.model_validate({"figure_type": "whatever"})
    assert weird.figure_type == "DIAGRAM"


def test_table_rows_to_latex_shape_and_escaping():
    latex = table_rows_to_latex([["Gene & Co", "50%"], ["BRCA_1", "Risk #2"]])
    assert r"\begin{tabular}" in latex and r"\end{tabular}" in latex
    assert r"Gene \& Co" in latex and r"50\%" in latex and r"BRCA\_1" in latex
    assert table_rows_to_latex([[], []]) == ""
    assert table_rows_to_latex([]) == ""


def test_figure_text_block_per_type():
    chart = {"index": 1, "caption": "Sales rise", "figure_type": "CHART", "markdown_table": "| y | v |"}
    block = _figure_text_block(chart, 2)
    assert "[Figure p2.1 (chart): Sales rise]" in block and "| y | v |" in block
    scan = {"index": 2, "caption": "Table", "figure_type": "TABLE_SCAN", "latex_table": "\\begin{tabular}"}
    block2 = _figure_text_block(scan, 2)
    assert "(table_scan)" in block2 and "```latex" in block2
    photo = {"index": 3, "caption": "A leaf", "figure_type": "PHOTO"}
    assert _figure_text_block(photo, 2) == "[Figure p2.3 (photo): A leaf]"
    enriched = _enrich_text("base text here", [], [chart], 2)
    assert "base text here" in enriched and "[Figure p2.1" in enriched


def test_analyze_returns_none_under_pytest_guard():
    assert os.getenv("PYTEST_CURRENT_TEST")  # sanity: guard is active
    assert vision_service.analyze_figure_bytes(b"fake-png") is None


def _diagram_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 300), "Mitochondria produce cellular energy through respiration daily")
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200))
    pix.clear_with(200)
    page.insert_image(fitz.Rect(72, 72, 272, 272), pixmap=pix)
    doc.save(path)
    doc.close()


def test_diagram_page_fallback_keeps_text_method_and_hash():
    d = tempfile.mkdtemp(prefix="fig_")
    p = os.path.join(d, "diagram.pdf")
    _diagram_pdf(p)
    with (
        patch("app.services.vision_service.analyze_figure_bytes", return_value=None) as mock_a,
        patch("app.services.vision_service.caption_image_bytes", return_value=None),
        patch("app.services.ocr_service.ocr_fitz_page") as mock_ocr,
    ):
        pages = extract_document_pages(p)
    assert pages[0]["extraction_method"] == "TEXT"
    assert mock_a.call_count == 1
    mock_ocr.assert_not_called()
    figs = pages[0]["figures"]
    assert len(figs) == 1
    assert figs[0]["figure_type"] == "DIAGRAM"
    assert len(figs[0]["image_hash"]) == 16
    assert figs[0].pop("_png_bytes", None)  # transient bytes carried for persistence
    assert "[Figure p1.1" in pages[0]["text"]


def test_decorative_figures_dropped():
    d = tempfile.mkdtemp(prefix="fig_")
    p = os.path.join(d, "deco.pdf")
    _diagram_pdf(p)
    with (
        patch(
            "app.services.vision_service.analyze_figure_bytes",
            return_value={"figure_type": "DECORATIVE", "summary": "", "markdown_table": None, "latex_table": None},
        ),
        patch("app.services.vision_service.caption_image_bytes") as mock_c,
    ):
        pages = extract_document_pages(p)
    assert pages[0]["figures"] == []
    assert "[Figure" not in pages[0]["text"]
    mock_c.assert_not_called()
