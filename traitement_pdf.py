#!/usr/bin/env python3
"""Traitement PDF - Outil de traitement de pièces PDF

Fonctionnalités :
- Division d'un fichier PDF en pièces selon des plages de pages
- Tamponnement de chaque page avec le numéro de pièce
- Numérotation des pages de chaque pièce
- Génération d'un bordereau de communication des pièces

Usage :
    python traitement_pdf.py input.pdf [--config config.json] [--output dossier_sortie]
    python traitement_pdf.py input.pdf --output dossier_sortie  (pièce unique)

Format du fichier de configuration JSON :
    {
        "titre_bordereau": "BORDEREAU DE COMMUNICATION DES PIÈCES",
        "pieces": [
            {"titre": "Contrat de vente", "page_debut": 1, "page_fin": 5},
            {"titre": "Annexe 1",         "page_debut": 6, "page_fin": 10}
        ]
    }
"""

import argparse
import json
import os
import sys
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def create_stamp(piece_num, page_num, total_pages, page_width, page_height):
    """Crée un tampon PDF (overlay) à appliquer sur une page.

    Args:
        piece_num: Numéro de la pièce.
        page_num: Numéro de la page courante dans la pièce (1-indexé).
        total_pages: Nombre total de pages dans la pièce.
        page_width: Largeur de la page en points.
        page_height: Hauteur de la page en points.

    Returns:
        BytesIO contenant le PDF du tampon.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    stamp_text = f"Pièce N° {piece_num}"
    font_name = "Helvetica-Bold"
    font_size = 10
    padding = 2 * mm
    margin = 10 * mm

    text_width = c.stringWidth(stamp_text, font_name, font_size)
    x = page_width - text_width - margin
    y = page_height - 14 * mm

    # Fond du tampon
    c.setFillColor(colors.HexColor("#E8F0F8"))
    c.setStrokeColor(colors.HexColor("#003366"))
    c.rect(
        x - padding,
        y - padding,
        text_width + 2 * padding,
        font_size + 2 * padding,
        fill=1,
        stroke=1,
    )

    # Texte du tampon
    c.setFillColor(colors.HexColor("#003366"))
    c.setFont(font_name, font_size)
    c.drawString(x, y, stamp_text)

    # Numéro de page en bas de page
    page_text = f"Page {page_num}/{total_pages}"
    page_font = "Helvetica"
    page_font_size = 8
    c.setFont(page_font, page_font_size)
    page_text_width = c.stringWidth(page_text, page_font, page_font_size)
    c.setFillColor(colors.grey)
    c.drawString((page_width - page_text_width) / 2, 8 * mm, page_text)

    c.save()
    buffer.seek(0)
    return buffer


def process_pdf(input_pdf_path, pieces_config, output_dir):
    """Traite un PDF : découpe en pièces et tamponne chaque page.

    Args:
        input_pdf_path: Chemin vers le fichier PDF source.
        pieces_config: Liste de dicts avec les clés ``titre``, ``page_debut``,
            ``page_fin`` (pages 1-indexées).
        output_dir: Répertoire de sortie pour les pièces.

    Returns:
        Liste de dicts avec les infos de chaque pièce traitée :
        ``numero``, ``titre``, ``pages``, ``fichier``.
    """
    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(input_pdf_path)
    total_pdf_pages = len(reader.pages)

    processed_pieces = []

    for i, piece in enumerate(pieces_config, start=1):
        piece_num = i
        piece_title = piece.get("titre", f"Pièce {i}")
        start_page = piece.get("page_debut", 1) - 1  # 0-indexé
        end_page = piece.get("page_fin", total_pdf_pages) - 1  # 0-indexé

        # Clamping des bornes
        start_page = max(0, min(start_page, total_pdf_pages - 1))
        end_page = max(start_page, min(end_page, total_pdf_pages - 1))

        num_pages = end_page - start_page + 1

        writer = PdfWriter()

        for j, page_idx in enumerate(range(start_page, end_page + 1)):
            page = reader.pages[page_idx]
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            stamp_buffer = create_stamp(
                piece_num, j + 1, num_pages, page_width, page_height
            )
            stamp_reader = PdfReader(stamp_buffer)
            stamp_page = stamp_reader.pages[0]

            writer.add_page(page)
            writer.pages[-1].merge_page(stamp_page)

        safe_title = piece_title.replace(" ", "_")[:30]
        output_filename = f"piece_{piece_num:02d}_{safe_title}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "wb") as f:
            writer.write(f)

        processed_pieces.append(
            {
                "numero": piece_num,
                "titre": piece_title,
                "pages": num_pages,
                "fichier": output_path,
            }
        )

    return processed_pieces


def generate_bordereau(pieces, output_path, title="BORDEREAU DE COMMUNICATION DES PIÈCES"):
    """Génère le bordereau de communication des pièces en PDF.

    Args:
        pieces: Liste de dicts avec ``numero``, ``titre``, ``pages``.
        output_path: Chemin de sortie du bordereau PDF.
        title: Titre affiché en en-tête du bordereau.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#003366"),
        spaceAfter=12,
    )

    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.5 * cm))

    table_data = [["N°", "DÉSIGNATION", "PAGES"]]
    total_pages = 0

    for piece in pieces:
        table_data.append(
            [str(piece["numero"]), piece["titre"], str(piece["pages"])]
        )
        total_pages += piece["pages"]

    table_data.append(["", "TOTAL", str(total_pages)])

    col_widths = [1.5 * cm, 13 * cm, 2 * cm]
    table = Table(table_data, colWidths=col_widths)

    table_style = TableStyle(
        [
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            # Lignes de données
            ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -2), 10),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F0F4F8")]),
            ("BOTTOMPADDING", (0, 1), (-1, -2), 6),
            ("TOPPADDING", (0, 1), (-1, -2), 6),
            # Ligne total
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F0F8")),
            ("ALIGN", (1, -1), (1, -1), "RIGHT"),
            # Bordures
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#003366")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#003366")),
        ]
    )

    table.setStyle(table_style)
    elements.append(table)
    doc.build(elements)


def load_config(config_path):
    """Charge la configuration depuis un fichier JSON.

    Args:
        config_path: Chemin vers le fichier de configuration JSON.

    Returns:
        Dict de configuration.

    Raises:
        SystemExit: Si le fichier est introuvable ou invalide.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erreur : fichier de configuration introuvable : {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Erreur : JSON invalide dans {config_path} : {exc}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Traitement PDF : découpe, tampon et bordereau de communication.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Fichier PDF source")
    parser.add_argument(
        "--config",
        "-c",
        help="Fichier de configuration JSON (définition des pièces)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="sortie",
        help="Répertoire de sortie (défaut : sortie/)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Erreur : fichier source introuvable : {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.config:
        config = load_config(args.config)
        pieces_config = config.get("pieces", [])
        bordereau_title = config.get(
            "titre_bordereau", "BORDEREAU DE COMMUNICATION DES PIÈCES"
        )
    else:
        # Pièce unique : tout le PDF
        reader = PdfReader(args.input)
        total_pages = len(reader.pages)
        pieces_config = [
            {
                "titre": os.path.splitext(os.path.basename(args.input))[0],
                "page_debut": 1,
                "page_fin": total_pages,
            }
        ]
        bordereau_title = "BORDEREAU DE COMMUNICATION DES PIÈCES"

    if not pieces_config:
        print("Erreur : aucune pièce définie dans la configuration.", file=sys.stderr)
        sys.exit(1)

    print(f"Traitement de « {args.input} » → {len(pieces_config)} pièce(s)…")

    pieces = process_pdf(args.input, pieces_config, args.output)

    bordereau_path = os.path.join(args.output, "bordereau.pdf")
    generate_bordereau(pieces, bordereau_path, bordereau_title)

    print(f"\nPièces générées dans « {args.output} » :")
    for piece in pieces:
        print(f"  Pièce {piece['numero']:02d} — {piece['titre']} ({piece['pages']} page(s))")
    print(f"\nBordereau : {bordereau_path}")


if __name__ == "__main__":
    main()
