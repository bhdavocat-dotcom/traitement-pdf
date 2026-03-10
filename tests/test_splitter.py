"""Tests unitaires pour le module splitter."""

import io
from pathlib import Path

import pytest
from pypdf import PdfWriter

from traitement_pdf.splitter import (
    _is_blank_page,
    _parse_page_ranges,
    save_pieces,
    split_by_blank_pages,
    split_by_page_ranges,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_pdf_with_text(texts: list, tmp_path: Path) -> str:
    """Crée un PDF temporaire dont chaque page contient le texte fourni.

    Les pages avec une chaîne vide (``""``) sont des pages vierges.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    path = tmp_path / "test_input.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    for text in texts:
        if text:
            c.drawString(72, 700, text)
        c.showPage()
    c.save()
    return str(path)


# ---------------------------------------------------------------------------
# _parse_page_ranges
# ---------------------------------------------------------------------------

class TestParsePageRanges:
    def test_single_page(self):
        result = _parse_page_ranges("3", 10)
        assert result == [(2, 2)]

    def test_range(self):
        result = _parse_page_ranges("1-3", 10)
        assert result == [(0, 2)]

    def test_multiple_ranges(self):
        result = _parse_page_ranges("1-3,4-6,7", 10)
        assert result == [(0, 2), (3, 5), (6, 6)]

    def test_strips_whitespace(self):
        result = _parse_page_ranges(" 1 - 3 , 4 - 6 ", 10)
        assert result == [(0, 2), (3, 5)]

    def test_invalid_syntax_raises(self):
        with pytest.raises(ValueError, match="invalide"):
            _parse_page_ranges("a-b", 10)

    def test_out_of_bounds_raises(self):
        with pytest.raises(ValueError, match="hors limites"):
            _parse_page_ranges("1-11", 10)

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError, match="hors limites"):
            _parse_page_ranges("5-3", 10)

    def test_empty_spec_raises(self):
        with pytest.raises(ValueError, match="vide"):
            _parse_page_ranges("", 10)


# ---------------------------------------------------------------------------
# split_by_page_ranges
# ---------------------------------------------------------------------------

class TestSplitByPageRanges:
    def test_produces_correct_number_of_pieces(self, tmp_path):
        pdf = _make_pdf_with_text(["Page 1", "Page 2", "Page 3", "Page 4"], tmp_path)
        writers = split_by_page_ranges(pdf, [(0, 1), (2, 3)])
        assert len(writers) == 2

    def test_pieces_have_correct_page_counts(self, tmp_path):
        pdf = _make_pdf_with_text(["P1", "P2", "P3", "P4", "P5"], tmp_path)
        writers = split_by_page_ranges(pdf, [(0, 2), (3, 4)])
        assert len(writers[0].pages) == 3
        assert len(writers[1].pages) == 2

    def test_single_page_piece(self, tmp_path):
        pdf = _make_pdf_with_text(["only"], tmp_path)
        writers = split_by_page_ranges(pdf, [(0, 0)])
        assert len(writers) == 1
        assert len(writers[0].pages) == 1


# ---------------------------------------------------------------------------
# split_by_blank_pages
# ---------------------------------------------------------------------------

class TestSplitByBlankPages:
    def test_splits_on_blank_separator(self, tmp_path):
        # 2 pièces séparées par une page vide
        pdf = _make_pdf_with_text(
            ["Doc A page 1", "Doc A page 2", "", "Doc B page 1"],
            tmp_path,
        )
        writers = split_by_blank_pages(pdf)
        assert len(writers) == 2
        assert len(writers[0].pages) == 2
        assert len(writers[1].pages) == 1

    def test_no_blank_page_returns_one_piece(self, tmp_path):
        pdf = _make_pdf_with_text(["P1", "P2", "P3"], tmp_path)
        writers = split_by_blank_pages(pdf)
        assert len(writers) == 1
        assert len(writers[0].pages) == 3

    def test_multiple_blank_separators(self, tmp_path):
        pdf = _make_pdf_with_text(
            ["A", "", "B", "B2", "", "C"],
            tmp_path,
        )
        writers = split_by_blank_pages(pdf)
        assert len(writers) == 3

    def test_leading_blank_pages_ignored(self, tmp_path):
        pdf = _make_pdf_with_text(["", "", "Content"], tmp_path)
        writers = split_by_blank_pages(pdf)
        assert len(writers) == 1


# ---------------------------------------------------------------------------
# save_pieces
# ---------------------------------------------------------------------------

class TestSavePieces:
    def test_files_created(self, tmp_path):
        writers = [PdfWriter(), PdfWriter()]
        for w in writers:
            w.add_blank_page(width=595, height=842)
        paths = save_pieces(writers, str(tmp_path / "output"))
        assert len(paths) == 2
        for p in paths:
            assert Path(p).exists()

    def test_filename_format(self, tmp_path):
        writers = [PdfWriter()]
        writers[0].add_blank_page(width=595, height=842)
        paths = save_pieces(writers, str(tmp_path / "out"), base_name="doc")
        assert Path(paths[0]).name == "doc_01.pdf"

    def test_output_dir_created(self, tmp_path):
        new_dir = tmp_path / "new" / "subdir"
        writers = [PdfWriter()]
        writers[0].add_blank_page(width=595, height=842)
        save_pieces(writers, str(new_dir))
        assert new_dir.exists()
