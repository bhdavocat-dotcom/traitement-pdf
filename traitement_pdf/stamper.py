"""Tamponnage des pièces : ajout du numéro de pièce sur chaque page.

Le tampon est apposé dans le coin supérieur droit de chaque page.
Il affiche « Pièce N°X » sur fond rouge, ainsi que le numéro de page
en bas à droite.
"""

import io
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas

# Couleur du tampon
_STAMP_BG = HexColor("#CC0000")


def _create_stamp_overlay(
    width: float,
    height: float,
    piece_number: int,
    piece_title: Optional[str],
    page_num: int,
    total_pages: int,
) -> io.BytesIO:
    """Crée une page PDF transparente portant uniquement le tampon.

    Args:
        width:        Largeur de la page cible (points).
        height:       Hauteur de la page cible (points).
        piece_number: Numéro de la pièce.
        piece_title:  Titre court de la pièce (tronqué à 22 caractères).
        page_num:     Numéro de la page courante dans la pièce.
        total_pages:  Nombre total de pages de la pièce.

    Returns:
        Buffer BytesIO positionné au début contenant le PDF overlay.
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))

    # --- Tampon principal (coin supérieur droit) ---
    label = f"Pièce N°{piece_number}"
    if piece_title:
        short = piece_title[:22] + "…" if len(piece_title) > 22 else piece_title
        label += f" – {short}"

    # Dimensionnement dynamique selon la longueur du texte
    font_size = 9
    box_w = min(len(label) * 5.5 + 10, width * 0.45)
    box_h = 18
    margin = 8
    box_x = width - box_w - margin
    box_y = height - box_h - margin

    c.setFillColor(_STAMP_BG)
    c.roundRect(box_x, box_y, box_w, box_h, radius=3, fill=True, stroke=False)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(box_x + box_w / 2, box_y + (box_h - font_size) / 2, label)

    # --- Numérotation de page (coin inférieur droit) ---
    page_label = f"{page_num}/{total_pages}"
    c.setFillColor(_STAMP_BG)
    c.setFont("Helvetica", 8)
    c.drawRightString(width - margin, margin, page_label)

    c.save()
    packet.seek(0)
    return packet


def stamp_pdf(
    input_path: str,
    output_path: str,
    piece_number: int,
    piece_title: Optional[str] = None,
) -> None:
    """Appose le tampon « Pièce N°X » sur toutes les pages du PDF.

    Args:
        input_path:   Chemin du PDF à tamponner.
        output_path:  Chemin du PDF de sortie.
        piece_number: Numéro de la pièce.
        piece_title:  Titre optionnel affiché dans le tampon.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()
    total = len(reader.pages)

    for idx, page in enumerate(reader.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        overlay_buf = _create_stamp_overlay(
            width, height, piece_number, piece_title, idx + 1, total
        )
        overlay_reader = PdfReader(overlay_buf)

        # Add page to writer first, then merge overlay (avoids deprecation warning)
        writer.add_page(page)
        writer.pages[-1].merge_page(overlay_reader.pages[0])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as fh:
        writer.write(fh)


def stamp_pieces(
    piece_paths: list,
    output_dir: str,
    titles: Optional[list] = None,
) -> list:
    """Tamponne une liste de fichiers PDF (pièces).

    Args:
        piece_paths: Liste des chemins des pièces à tamponner.
        output_dir:  Répertoire de sortie.
        titles:      Liste optionnelle de titres (doit avoir la même longueur
                     que *piece_paths* si fournie).

    Returns:
        Liste des chemins des pièces tamponnées.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamped: list = []

    for i, path in enumerate(piece_paths, start=1):
        title = titles[i - 1] if titles and i - 1 < len(titles) else None
        out_path = out / Path(path).name
        stamp_pdf(str(path), str(out_path), i, title)
        stamped.append(str(out_path))

    return stamped
