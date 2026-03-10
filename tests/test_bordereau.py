"""Tests unitaires pour le module bordereau."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from traitement_pdf.bordereau import generate_bordereau, pieces_from_paths


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PIECES = [
    (1, "Contrat de bail", 3, "Signé le 01/01/2024"),
    (2, "Acte de naissance", 1, ""),
    (3, "Correspondance email", 2, "Imprimé"),
]


def _make_simple_pdf(tmp_path: Path, pages: int = 2, name: str = "piece.pdf") -> str:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    path = tmp_path / name
    c = canvas.Canvas(str(path), pagesize=A4)
    for i in range(pages):
        c.drawString(72, 700, f"Page {i + 1}")
        c.showPage()
    c.save()
    return str(path)


# ---------------------------------------------------------------------------
# generate_bordereau
# ---------------------------------------------------------------------------

class TestGenerateBordereau:
    def test_output_file_created(self, tmp_path):
        out = str(tmp_path / "bordereau.pdf")
        generate_bordereau(SAMPLE_PIECES, out)
        assert Path(out).exists()

    def test_output_is_valid_pdf(self, tmp_path):
        out = str(tmp_path / "bordereau.pdf")
        generate_bordereau(SAMPLE_PIECES, out)
        reader = PdfReader(out)
        assert reader.pages

    def test_with_metadata(self, tmp_path):
        out = str(tmp_path / "bordereau.pdf")
        generate_bordereau(
            SAMPLE_PIECES,
            out,
            dossier="2024/001",
            partie="Maître Dupont",
            adversaire="Maître Martin",
            juridiction="Tribunal judiciaire de Paris",
        )
        assert Path(out).exists()

    def test_single_piece(self, tmp_path):
        out = str(tmp_path / "bordereau.pdf")
        generate_bordereau([(1, "Seule pièce", 5, "")], out)
        reader = PdfReader(out)
        assert reader.pages

    def test_many_pieces(self, tmp_path):
        """Le tableau doit tenir sur plusieurs pages sans erreur."""
        pieces = [(i, f"Pièce numéro {i}", i % 5 + 1, "") for i in range(1, 31)]
        out = str(tmp_path / "bordereau.pdf")
        generate_bordereau(pieces, out)
        assert Path(out).exists()

    def test_output_dir_created(self, tmp_path):
        out = str(tmp_path / "sub" / "dir" / "bordereau.pdf")
        generate_bordereau(SAMPLE_PIECES, out)
        assert Path(out).exists()

    def test_empty_observations(self, tmp_path):
        pieces = [(1, "Pièce", 1, ""), (2, "Autre", 2, None)]
        out = str(tmp_path / "bordereau.pdf")
        generate_bordereau(pieces, out)
        assert Path(out).exists()


# ---------------------------------------------------------------------------
# pieces_from_paths
# ---------------------------------------------------------------------------

class TestPiecesFromPaths:
    def test_basic(self, tmp_path):
        pdf = _make_simple_pdf(tmp_path, pages=3)
        result = pieces_from_paths([pdf])
        assert len(result) == 1
        numero, designation, nb_pages, obs = result[0]
        assert numero == 1
        assert nb_pages == 3
        assert obs == ""

    def test_with_titles(self, tmp_path):
        pdf = _make_simple_pdf(tmp_path, pages=2)
        result = pieces_from_paths([pdf], titles=["Mon titre"])
        assert result[0][1] == "Mon titre"

    def test_without_titles_uses_filename(self, tmp_path):
        pdf = _make_simple_pdf(tmp_path, name="contrat_bail.pdf")
        result = pieces_from_paths([pdf])
        assert "contrat" in result[0][1].lower() or "bail" in result[0][1].lower()

    def test_with_observations(self, tmp_path):
        pdf = _make_simple_pdf(tmp_path)
        result = pieces_from_paths([pdf], observations=["Signé"])
        assert result[0][3] == "Signé"

    def test_multiple_pieces(self, tmp_path):
        pdfs = [
            _make_simple_pdf(tmp_path, pages=i + 1, name=f"p{i}.pdf")
            for i in range(3)
        ]
        result = pieces_from_paths(pdfs)
        assert len(result) == 3
        assert [r[0] for r in result] == [1, 2, 3]
        assert [r[2] for r in result] == [1, 2, 3]
