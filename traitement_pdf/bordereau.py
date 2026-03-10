"""Génération du bordereau de communication des pièces.

Le bordereau est un document PDF au format A4 portrait qui récapitule
toutes les pièces communiquées : numéro, désignation, nombre de pages
et observations éventuelles.
"""

from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_styles = getSampleStyleSheet()

_TITLE_STYLE = ParagraphStyle(
    "BordereauTitle",
    parent=_styles["Heading1"],
    fontSize=14,
    textColor=colors.HexColor("#1A1A6E"),
    spaceAfter=6,
    alignment=1,  # centré
)

_SUBTITLE_STYLE = ParagraphStyle(
    "BordereauSubtitle",
    parent=_styles["Normal"],
    fontSize=10,
    textColor=colors.grey,
    spaceAfter=4,
    alignment=1,
)

_CELL_STYLE = ParagraphStyle(
    "CellStyle",
    parent=_styles["Normal"],
    fontSize=9,
    leading=12,
)

_HEADER_STYLE = ParagraphStyle(
    "HeaderStyle",
    parent=_styles["Normal"],
    fontSize=9,
    textColor=colors.white,
    fontName="Helvetica-Bold",
    alignment=1,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

PieceInfo = Tuple[int, str, int, str]
"""Type d'une entrée de pièce : (numéro, désignation, nb_pages, observations)."""


def generate_bordereau(
    pieces: List[PieceInfo],
    output_path: str,
    dossier: Optional[str] = None,
    partie: Optional[str] = None,
    adversaire: Optional[str] = None,
    juridiction: Optional[str] = None,
) -> None:
    """Génère le bordereau de communication des pièces en PDF.

    Args:
        pieces:      Liste de tuples ``(numero, designation, nb_pages, observations)``.
        output_path: Chemin du PDF à générer.
        dossier:     Référence du dossier (optionnel).
        partie:      Nom de la partie communiquante (optionnel).
        adversaire:  Nom de la partie adverse (optionnel).
        juridiction: Nom de la juridiction (optionnel).
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []

    # --- En-tête ---
    story.append(Paragraph("BORDEREAU DE COMMUNICATION DES PIÈCES", _TITLE_STYLE))
    story.append(Spacer(1, 0.3 * cm))

    today = date.today().strftime("%d/%m/%Y")
    if dossier:
        story.append(Paragraph(f"Dossier : {dossier}", _SUBTITLE_STYLE))
    if juridiction:
        story.append(Paragraph(f"Juridiction : {juridiction}", _SUBTITLE_STYLE))
    if partie:
        story.append(Paragraph(f"Communiqué par : {partie}", _SUBTITLE_STYLE))
    if adversaire:
        story.append(Paragraph(f"À : {adversaire}", _SUBTITLE_STYLE))
    story.append(Paragraph(f"Date : {today}", _SUBTITLE_STYLE))
    story.append(Spacer(1, 0.6 * cm))

    # --- Tableau ---
    page_width = A4[0] - 4 * cm  # marges gauche + droite

    col_widths = [
        1.5 * cm,   # N°
        page_width * 0.50,  # Désignation
        2.0 * cm,   # Nb pages
        page_width * 0.30,  # Observations
    ]

    headers = [
        Paragraph("N°", _HEADER_STYLE),
        Paragraph("Désignation de la pièce", _HEADER_STYLE),
        Paragraph("Pages", _HEADER_STYLE),
        Paragraph("Observations", _HEADER_STYLE),
    ]

    table_data = [headers]
    for numero, designation, nb_pages, observations in pieces:
        row = [
            Paragraph(str(numero), _CELL_STYLE),
            Paragraph(designation, _CELL_STYLE),
            Paragraph(str(nb_pages), _CELL_STYLE),
            Paragraph(observations or "", _CELL_STYLE),
        ]
        table_data.append(row)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    header_bg = colors.HexColor("#1A1A6E")
    row_alt = colors.HexColor("#EEF0F8")

    ts = TableStyle(
        [
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            # Lignes alternées
            *[
                ("BACKGROUND", (0, r), (-1, r), row_alt)
                for r in range(2, len(table_data), 2)
            ],
            # Bordures
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAAACC")),
            ("ROWBACKGROUND", (0, 1), (-1, -1), colors.white),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]
    )
    # Réappliquer la couleur alternée par-dessus ROWBACKGROUND
    for r in range(2, len(table_data), 2):
        ts.add("BACKGROUND", (0, r), (-1, r), row_alt)

    table.setStyle(ts)
    story.append(table)

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            f"Total : {len(pieces)} pièce(s) — "
            f"{sum(p[2] for p in pieces)} page(s)",
            _SUBTITLE_STYLE,
        )
    )

    doc.build(story)


def pieces_from_paths(
    paths: List[str],
    titles: Optional[List[str]] = None,
    observations: Optional[List[str]] = None,
) -> List[PieceInfo]:
    """Construit la liste des pièces à partir de chemins de fichiers PDF.

    Args:
        paths:        Liste des chemins des pièces (tamponnées ou non).
        titles:       Titres des pièces (si None, déduit du nom de fichier).
        observations: Observations par pièce (optionnel).

    Returns:
        Liste de :data:`PieceInfo`.
    """
    from pypdf import PdfReader

    pieces: List[PieceInfo] = []
    for i, path in enumerate(paths, start=1):
        reader = PdfReader(path)
        nb_pages = len(reader.pages)

        if titles and i - 1 < len(titles):
            designation = titles[i - 1]
        else:
            # Utiliser le nom du fichier sans extension
            designation = Path(path).stem.replace("_", " ").capitalize()

        obs = observations[i - 1] if observations and i - 1 < len(observations) else ""
        pieces.append((i, designation, nb_pages, obs))

    return pieces
