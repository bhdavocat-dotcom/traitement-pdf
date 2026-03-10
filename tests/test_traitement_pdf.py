"""Tests unitaires pour traitement_pdf.py"""

import json
import os
import sys
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from traitement_pdf import (
    create_stamp,
    generate_bordereau,
    load_config,
    process_pdf,
)


def make_test_pdf(num_pages=5, pagesize=A4):
    """Crée un fichier PDF de test avec num_pages pages vierges."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=pagesize)
    for i in range(1, num_pages + 1):
        c.drawString(72, pagesize[1] - 72, f"Page {i}")
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def save_test_pdf(path, num_pages=5):
    """Enregistre un PDF de test sur disque."""
    buf = make_test_pdf(num_pages)
    with open(path, "wb") as f:
        f.write(buf.read())


class TestCreateStamp(unittest.TestCase):
    def test_returns_valid_pdf(self):
        buf = create_stamp(1, 1, 3, A4[0], A4[1])
        reader = PdfReader(buf)
        self.assertEqual(len(reader.pages), 1)

    def test_stamp_page_dimensions(self):
        w, h = A4
        buf = create_stamp(2, 2, 5, w, h)
        reader = PdfReader(buf)
        page = reader.pages[0]
        self.assertAlmostEqual(float(page.mediabox.width), w, places=1)
        self.assertAlmostEqual(float(page.mediabox.height), h, places=1)

    def test_different_piece_numbers(self):
        for num in [1, 5, 99]:
            buf = create_stamp(num, 1, 1, A4[0], A4[1])
            reader = PdfReader(buf)
            self.assertEqual(len(reader.pages), 1)


class TestProcessPdf(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.input_pdf = os.path.join(self.tmpdir, "test_input.pdf")
        save_test_pdf(self.input_pdf, num_pages=6)

    def test_single_piece_full_pdf(self):
        config = [{"titre": "Pièce unique", "page_debut": 1, "page_fin": 6}]
        out_dir = os.path.join(self.tmpdir, "output")
        pieces = process_pdf(self.input_pdf, config, out_dir)

        self.assertEqual(len(pieces), 1)
        self.assertEqual(pieces[0]["numero"], 1)
        self.assertEqual(pieces[0]["titre"], "Pièce unique")
        self.assertEqual(pieces[0]["pages"], 6)
        self.assertTrue(os.path.isfile(pieces[0]["fichier"]))

    def test_multiple_pieces(self):
        config = [
            {"titre": "Contrat", "page_debut": 1, "page_fin": 3},
            {"titre": "Annexe", "page_debut": 4, "page_fin": 6},
        ]
        out_dir = os.path.join(self.tmpdir, "output_multi")
        pieces = process_pdf(self.input_pdf, config, out_dir)

        self.assertEqual(len(pieces), 2)
        self.assertEqual(pieces[0]["pages"], 3)
        self.assertEqual(pieces[1]["pages"], 3)
        for piece in pieces:
            self.assertTrue(os.path.isfile(piece["fichier"]))

    def test_output_pdf_page_count(self):
        config = [{"titre": "Doc", "page_debut": 2, "page_fin": 4}]
        out_dir = os.path.join(self.tmpdir, "output_count")
        pieces = process_pdf(self.input_pdf, config, out_dir)

        reader = PdfReader(pieces[0]["fichier"])
        self.assertEqual(len(reader.pages), 3)

    def test_page_range_clamping(self):
        """Les bornes hors plage doivent être ramenées à la plage valide."""
        config = [{"titre": "Test", "page_debut": 0, "page_fin": 100}]
        out_dir = os.path.join(self.tmpdir, "output_clamp")
        pieces = process_pdf(self.input_pdf, config, out_dir)
        self.assertEqual(pieces[0]["pages"], 6)

    def test_output_dir_created(self):
        config = [{"titre": "P1", "page_debut": 1, "page_fin": 2}]
        out_dir = os.path.join(self.tmpdir, "new_output_dir")
        self.assertFalse(os.path.isdir(out_dir))
        process_pdf(self.input_pdf, config, out_dir)
        self.assertTrue(os.path.isdir(out_dir))

    def test_filename_uses_piece_number_and_title(self):
        config = [{"titre": "Mon Document", "page_debut": 1, "page_fin": 2}]
        out_dir = os.path.join(self.tmpdir, "output_fn")
        pieces = process_pdf(self.input_pdf, config, out_dir)
        basename = os.path.basename(pieces[0]["fichier"])
        self.assertIn("piece_01", basename)
        self.assertIn("Mon_Document", basename)


class TestGenerateBordereau(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pieces = [
            {"numero": 1, "titre": "Contrat", "pages": 3, "fichier": "piece_01.pdf"},
            {"numero": 2, "titre": "Annexe 1", "pages": 5, "fichier": "piece_02.pdf"},
        ]

    def test_generates_pdf_file(self):
        out = os.path.join(self.tmpdir, "bordereau.pdf")
        generate_bordereau(self.pieces, out)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_generated_pdf_is_readable(self):
        out = os.path.join(self.tmpdir, "bordereau_read.pdf")
        generate_bordereau(self.pieces, out)
        reader = PdfReader(out)
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_custom_title(self):
        out = os.path.join(self.tmpdir, "bordereau_custom.pdf")
        generate_bordereau(self.pieces, out, title="MON BORDEREAU PERSONNALISÉ")
        self.assertTrue(os.path.isfile(out))

    def test_single_piece(self):
        pieces = [{"numero": 1, "titre": "Document unique", "pages": 10, "fichier": "p.pdf"}]
        out = os.path.join(self.tmpdir, "bordereau_single.pdf")
        generate_bordereau(pieces, out)
        self.assertTrue(os.path.isfile(out))


class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_valid_config(self):
        config_data = {
            "titre_bordereau": "TEST",
            "pieces": [{"titre": "P1", "page_debut": 1, "page_fin": 2}],
        }
        path = os.path.join(self.tmpdir, "config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        config = load_config(path)
        self.assertEqual(config["titre_bordereau"], "TEST")
        self.assertEqual(len(config["pieces"]), 1)

    def test_file_not_found(self):
        with self.assertRaises(SystemExit):
            load_config("/nonexistent/path/config.json")

    def test_invalid_json(self):
        path = os.path.join(self.tmpdir, "bad.json")
        with open(path, "w") as f:
            f.write("{invalid json}")
        with self.assertRaises(SystemExit):
            load_config(path)


if __name__ == "__main__":
    unittest.main()
