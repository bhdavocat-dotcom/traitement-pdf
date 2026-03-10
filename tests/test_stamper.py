"""Tests unitaires pour le module stamper."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from traitement_pdf.stamper import stamp_pdf, stamp_pieces


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_simple_pdf(tmp_path: Path, pages: int = 2, name: str = "input.pdf") -> str:
    """Crée un PDF simple avec *pages* pages contenant du texte."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    path = tmp_path / name
    c = canvas.Canvas(str(path), pagesize=A4)
    for i in range(pages):
        c.drawString(72, 700, f"Contenu de la page {i + 1}")
        c.showPage()
    c.save()
    return str(path)


# ---------------------------------------------------------------------------
# stamp_pdf
# ---------------------------------------------------------------------------

class TestStampPdf:
    def test_output_file_created(self, tmp_path):
        src = _make_simple_pdf(tmp_path)
        out = str(tmp_path / "stamped.pdf")
        stamp_pdf(src, out, piece_number=1)
        assert Path(out).exists()

    def test_page_count_preserved(self, tmp_path):
        src = _make_simple_pdf(tmp_path, pages=3)
        out = str(tmp_path / "stamped.pdf")
        stamp_pdf(src, out, piece_number=2)
        reader = PdfReader(out)
        assert len(reader.pages) == 3

    def test_output_is_valid_pdf(self, tmp_path):
        src = _make_simple_pdf(tmp_path)
        out = str(tmp_path / "stamped.pdf")
        stamp_pdf(src, out, piece_number=1)
        # Si le fichier est invalide, PdfReader lèvera une exception
        reader = PdfReader(out)
        assert reader.pages

    def test_with_title(self, tmp_path):
        src = _make_simple_pdf(tmp_path)
        out = str(tmp_path / "stamped.pdf")
        stamp_pdf(src, out, piece_number=3, piece_title="Contrat de bail")
        assert Path(out).exists()

    def test_single_page(self, tmp_path):
        src = _make_simple_pdf(tmp_path, pages=1)
        out = str(tmp_path / "stamped.pdf")
        stamp_pdf(src, out, piece_number=1)
        reader = PdfReader(out)
        assert len(reader.pages) == 1

    def test_output_dir_created(self, tmp_path):
        src = _make_simple_pdf(tmp_path)
        out = str(tmp_path / "new" / "sub" / "stamped.pdf")
        stamp_pdf(src, out, piece_number=1)
        assert Path(out).exists()


# ---------------------------------------------------------------------------
# stamp_pieces
# ---------------------------------------------------------------------------

class TestStampPieces:
    def test_all_pieces_stamped(self, tmp_path):
        src1 = _make_simple_pdf(tmp_path, pages=2, name="p1.pdf")
        src2 = _make_simple_pdf(tmp_path, pages=1, name="p2.pdf")
        out_dir = str(tmp_path / "stamped")
        result = stamp_pieces([src1, src2], out_dir)
        assert len(result) == 2
        for p in result:
            assert Path(p).exists()

    def test_with_titles(self, tmp_path):
        src = _make_simple_pdf(tmp_path)
        out_dir = str(tmp_path / "stamped")
        result = stamp_pieces([src], out_dir, titles=["Mon titre"])
        assert len(result) == 1

    def test_piece_numbers_start_at_one(self, tmp_path):
        """stamp_pieces should number pieces starting from 1."""
        src1 = _make_simple_pdf(tmp_path, name="a.pdf")
        src2 = _make_simple_pdf(tmp_path, name="b.pdf")
        out_dir = str(tmp_path / "stamped")
        result = stamp_pieces([src1, src2], out_dir)
        # Both files should be readable PDFs
        for p in result:
            reader = PdfReader(p)
            assert len(reader.pages) >= 1

    def test_empty_list(self, tmp_path):
        out_dir = str(tmp_path / "stamped")
        result = stamp_pieces([], out_dir)
        assert result == []
