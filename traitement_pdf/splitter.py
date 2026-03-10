"""Découpage d'un PDF en pièces selon le contenu.

Trois stratégies sont disponibles :
- ``pages``    : plages de pages fournies par l'utilisateur ("1-3,4-6,7").
- ``blank``    : pages quasi-vides utilisées comme séparateurs.
- ``bookmarks``: signets (outlines) du fichier PDF.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from pypdf import PdfReader, PdfWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_page_ranges(spec: str, total_pages: int) -> List[Tuple[int, int]]:
    """Convertit une chaîne comme ``"1-3,4-6,7"`` en liste de tuples 0-indexés.

    Args:
        spec:        Chaîne de plages (ex. ``"1-3,4-6,7"``).
        total_pages: Nombre total de pages dans le fichier.

    Returns:
        Liste de tuples ``(debut, fin)`` en indices 0-based, bornes incluses.

    Raises:
        ValueError: Si la syntaxe est invalide ou les indices hors limites.
    """
    ranges: List[Tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        part_no_space = re.sub(r"\s+", "", part)
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part_no_space)
        if not m:
            raise ValueError(f"Plage invalide : {part!r}")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        part = part_no_space  # use cleaned version in error messages
        if start < 1 or end < start or end > total_pages:
            raise ValueError(
                f"Plage {part!r} hors limites (1-{total_pages})."
            )
        ranges.append((start - 1, end - 1))  # 0-indexed
    if not ranges:
        raise ValueError("La spécification de plages est vide.")
    return ranges


def _is_blank_page(page) -> bool:
    """Retourne True si la page ne contient aucun texte visible."""
    text = page.extract_text() or ""
    return not text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def split_by_page_ranges(
    input_path: str,
    page_ranges: List[Tuple[int, int]],
) -> List[PdfWriter]:
    """Découpe le PDF selon des plages de pages 0-indexées.

    Args:
        input_path:  Chemin vers le PDF source.
        page_ranges: Liste de ``(debut, fin)`` 0-indexés, bornes incluses.

    Returns:
        Liste de :class:`~pypdf.PdfWriter`, un par pièce.
    """
    reader = PdfReader(input_path)
    writers: List[PdfWriter] = []
    for start, end in page_ranges:
        writer = PdfWriter()
        for i in range(start, end + 1):
            writer.add_page(reader.pages[i])
        writers.append(writer)
    return writers


def split_by_blank_pages(input_path: str) -> List[PdfWriter]:
    """Découpe le PDF en utilisant les pages vides comme séparateurs.

    Les pages vides elles-mêmes sont exclues du résultat.

    Args:
        input_path: Chemin vers le PDF source.

    Returns:
        Liste de :class:`~pypdf.PdfWriter`, un par pièce.

    Raises:
        ValueError: Si aucune page non-vide n'est trouvée.
    """
    reader = PdfReader(input_path)
    writers: List[PdfWriter] = []
    current: Optional[PdfWriter] = None

    for page in reader.pages:
        if _is_blank_page(page):
            if current is not None and len(current.pages) > 0:
                writers.append(current)
                current = None
        else:
            if current is None:
                current = PdfWriter()
            current.add_page(page)

    if current is not None and len(current.pages) > 0:
        writers.append(current)

    if not writers:
        raise ValueError(
            "Aucune pièce trouvée : le fichier ne contient pas de pages "
            "séparatrices vides ou est entièrement vide."
        )
    return writers


def split_by_bookmarks(input_path: str) -> List[Tuple[PdfWriter, str]]:
    """Découpe le PDF selon ses signets de premier niveau.

    Args:
        input_path: Chemin vers le PDF source.

    Returns:
        Liste de tuples ``(PdfWriter, titre_signet)``.

    Raises:
        ValueError: Si aucun signet n'est trouvé dans le fichier.
    """
    reader = PdfReader(input_path)
    outlines = reader.outline
    if not outlines:
        raise ValueError(
            "Aucun signet trouvé dans le fichier PDF."
        )

    # Résoudre les signets de premier niveau → numéros de page (0-based)
    def _page_number(dest) -> int:
        if isinstance(dest, list):
            dest = dest[0]
        return reader.get_destination_page_number(dest)

    top_level = [item for item in outlines if not isinstance(item, list)]
    if not top_level:
        raise ValueError("Aucun signet de premier niveau trouvé.")

    # Construire les plages
    page_count = len(reader.pages)
    pieces: List[Tuple[PdfWriter, str]] = []
    for idx, dest in enumerate(top_level):
        title = dest.title if hasattr(dest, "title") else f"Pièce {idx + 1}"
        start = _page_number(dest)
        end = (
            _page_number(top_level[idx + 1]) - 1
            if idx + 1 < len(top_level)
            else page_count - 1
        )
        writer = PdfWriter()
        for i in range(start, end + 1):
            writer.add_page(reader.pages[i])
        pieces.append((writer, title))

    return pieces


def save_pieces(
    writers: List[PdfWriter],
    output_dir: str,
    base_name: str = "piece",
) -> List[str]:
    """Enregistre les pièces sur le disque.

    Args:
        writers:    Liste de :class:`~pypdf.PdfWriter`.
        output_dir: Répertoire de sortie (créé si nécessaire).
        base_name:  Préfixe des fichiers générés.

    Returns:
        Liste des chemins des fichiers créés.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: List[str] = []
    for i, writer in enumerate(writers, start=1):
        path = out / f"{base_name}_{i:02d}.pdf"
        with open(path, "wb") as fh:
            writer.write(fh)
        paths.append(str(path))
    return paths
