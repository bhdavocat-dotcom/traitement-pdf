#!/usr/bin/env python3
"""Traitement PDF – Interface en ligne de commande.

Commandes disponibles
---------------------
traiter   Traitement complet : découpage, tamponnage, bordereau.
split     Découper un PDF selon son contenu.
stamp     Tamponner des pièces PDF.
bordereau Générer le bordereau de communication des pièces.

Exemples
--------
# Traitement complet depuis un PDF avec séparateurs vides
python main.py traiter document.pdf --output-dir ./pieces/

# Traitement complet avec plages de pages explicites et titres
python main.py traiter document.pdf \\
    --methode pages --pages "1-5,6-12,13" \\
    --titres "Contrat" "Bail" "Correspondance" \\
    --output-dir ./pieces/

# Découpage seul
python main.py split document.pdf --methode blank --output-dir ./split/

# Tamponnage seul de fichiers existants
python main.py stamp piece_01.pdf piece_02.pdf --output-dir ./stamped/

# Bordereau seul à partir d'un répertoire de pièces
python main.py bordereau ./stamped/ --output bordereau.pdf
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

import click

from traitement_pdf.bordereau import generate_bordereau, pieces_from_paths
from traitement_pdf.splitter import (
    _parse_page_ranges,
    save_pieces,
    split_by_blank_pages,
    split_by_bookmarks,
    split_by_page_ranges,
)
from traitement_pdf.stamper import stamp_pdf, stamp_pieces


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_titles(titles_raw: Tuple[str, ...]) -> Optional[list]:
    """Retourne None si la liste est vide, sinon la liste."""
    return list(titles_raw) if titles_raw else None


def _pdf_files_in_dir(directory: str) -> list:
    """Retourne les fichiers PDF d'un répertoire, triés par nom."""
    return sorted(Path(directory).glob("*.pdf"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """Traitement PDF – Gestion des pièces juridiques.

    Découpe, tamponne et numérotate les pièces d'un dossier et génère
    le bordereau de communication correspondant.
    """


# ---- traiter ---------------------------------------------------------------

@cli.command()
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--output-dir", "-o",
    default="./pieces",
    show_default=True,
    help="Répertoire de sortie.",
)
@click.option(
    "--methode", "-m",
    type=click.Choice(["blank", "pages", "bookmarks"], case_sensitive=False),
    default="blank",
    show_default=True,
    help=(
        "Méthode de découpage : "
        "'blank' = pages vides séparatrices, "
        "'pages' = plages explicites (voir --pages), "
        "'bookmarks' = signets du PDF."
    ),
)
@click.option(
    "--pages", "-p",
    default=None,
    help="Plages de pages (ex. '1-3,4-6,7'). Utilisé uniquement avec --methode pages.",
)
@click.option(
    "--titres", "-t",
    multiple=True,
    metavar="TITRE",
    help="Titre de chaque pièce (répétez l'option pour chaque pièce).",
)
@click.option(
    "--dossier", default=None, help="Référence du dossier (bordereau)."
)
@click.option(
    "--partie", default=None, help="Nom de la partie communiquante (bordereau)."
)
@click.option(
    "--adversaire", default=None, help="Nom de la partie adverse (bordereau)."
)
@click.option(
    "--juridiction", default=None, help="Nom de la juridiction (bordereau)."
)
def traiter(
    input_pdf,
    output_dir,
    methode,
    pages,
    titres,
    dossier,
    partie,
    adversaire,
    juridiction,
):
    """Traitement complet : découpage, tamponnage et bordereau.

    INPUT_PDF  Fichier PDF à traiter.
    """
    out = Path(output_dir)
    split_dir = out / "split"
    stamped_dir = out / "stamped"

    titles = _resolve_titles(titres)

    # 1. Découpage
    click.echo(f"[1/3] Découpage du fichier '{input_pdf}' (méthode : {methode})…")
    try:
        if methode == "pages":
            if not pages:
                raise click.UsageError(
                    "L'option --pages est requise avec --methode pages."
                )
            from pypdf import PdfReader
            total = len(PdfReader(input_pdf).pages)
            ranges = _parse_page_ranges(pages, total)
            writers = split_by_page_ranges(input_pdf, ranges)
            piece_paths = save_pieces(writers, str(split_dir))
        elif methode == "blank":
            writers = split_by_blank_pages(input_pdf)
            piece_paths = save_pieces(writers, str(split_dir))
        else:  # bookmarks
            result = split_by_bookmarks(input_pdf)
            bk_writers = [w for w, _ in result]
            bk_titles = [t for _, t in result]
            if titles is None:
                titles = bk_titles
            piece_paths = save_pieces(bk_writers, str(split_dir))
    except (ValueError, Exception) as exc:
        click.echo(f"Erreur lors du découpage : {exc}", err=True)
        sys.exit(1)

    click.echo(f"    {len(piece_paths)} pièce(s) extraite(s) dans '{split_dir}'.")

    # 2. Tamponnage
    click.echo("[2/3] Tamponnage des pièces…")
    stamped_paths = stamp_pieces(piece_paths, str(stamped_dir), titles)
    click.echo(f"    Pièces tamponnées dans '{stamped_dir}'.")

    # 3. Bordereau
    click.echo("[3/3] Génération du bordereau…")
    piece_infos = pieces_from_paths(stamped_paths, titles)
    bordereau_path = str(out / "bordereau.pdf")
    generate_bordereau(
        piece_infos,
        bordereau_path,
        dossier=dossier,
        partie=partie,
        adversaire=adversaire,
        juridiction=juridiction,
    )
    click.echo(f"    Bordereau généré : '{bordereau_path}'.")
    click.echo("Terminé ✓")


# ---- split -----------------------------------------------------------------

@cli.command()
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--output-dir", "-o",
    default="./split",
    show_default=True,
    help="Répertoire de sortie.",
)
@click.option(
    "--methode", "-m",
    type=click.Choice(["blank", "pages", "bookmarks"], case_sensitive=False),
    default="blank",
    show_default=True,
    help="Méthode de découpage.",
)
@click.option(
    "--pages", "-p",
    default=None,
    help="Plages de pages (ex. '1-3,4-6'). Utilisé avec --methode pages.",
)
def split(input_pdf, output_dir, methode, pages):
    """Découper un PDF selon son contenu.

    INPUT_PDF  Fichier PDF à découper.
    """
    try:
        if methode == "pages":
            if not pages:
                raise click.UsageError(
                    "L'option --pages est requise avec --methode pages."
                )
            from pypdf import PdfReader
            total = len(PdfReader(input_pdf).pages)
            ranges = _parse_page_ranges(pages, total)
            writers = split_by_page_ranges(input_pdf, ranges)
        elif methode == "blank":
            writers = split_by_blank_pages(input_pdf)
        else:
            result = split_by_bookmarks(input_pdf)
            writers = [w for w, _ in result]
    except (ValueError, Exception) as exc:
        click.echo(f"Erreur : {exc}", err=True)
        sys.exit(1)

    paths = save_pieces(writers, output_dir)
    click.echo(f"{len(paths)} pièce(s) extraite(s) dans '{output_dir}'.")
    for p in paths:
        click.echo(f"  {p}")


# ---- stamp -----------------------------------------------------------------

@cli.command()
@click.argument("pieces", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--output-dir", "-o",
    default="./stamped",
    show_default=True,
    help="Répertoire de sortie.",
)
@click.option(
    "--titres", "-t",
    multiple=True,
    metavar="TITRE",
    help="Titre de chaque pièce (répétez l'option pour chaque pièce).",
)
def stamp(pieces, output_dir, titres):
    """Tamponner des pièces PDF existantes.

    PIECES  Un ou plusieurs fichiers PDF à tamponner.
    """
    titles = _resolve_titles(titres)
    stamped = stamp_pieces(list(pieces), output_dir, titles)
    click.echo(f"{len(stamped)} pièce(s) tamponnée(s) dans '{output_dir}'.")
    for p in stamped:
        click.echo(f"  {p}")


# ---- bordereau -------------------------------------------------------------

@cli.command()
@click.argument(
    "pieces_dir",
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    "--output", "-o",
    default="bordereau.pdf",
    show_default=True,
    help="Chemin du bordereau PDF à générer.",
)
@click.option(
    "--titres", "-t",
    multiple=True,
    metavar="TITRE",
    help="Titre de chaque pièce (dans l'ordre des fichiers).",
)
@click.option(
    "--dossier", default=None, help="Référence du dossier."
)
@click.option(
    "--partie", default=None, help="Nom de la partie communiquante."
)
@click.option(
    "--adversaire", default=None, help="Nom de la partie adverse."
)
@click.option(
    "--juridiction", default=None, help="Nom de la juridiction."
)
def bordereau(pieces_dir, output, titres, dossier, partie, adversaire, juridiction):
    """Générer le bordereau de communication des pièces.

    PIECES_DIR  Répertoire contenant les pièces PDF.
    """
    pdf_files = _pdf_files_in_dir(pieces_dir)
    if not pdf_files:
        click.echo(f"Aucun fichier PDF trouvé dans '{pieces_dir}'.", err=True)
        sys.exit(1)

    titles = _resolve_titles(titres)
    piece_infos = pieces_from_paths([str(p) for p in pdf_files], titles)
    generate_bordereau(
        piece_infos,
        output,
        dossier=dossier,
        partie=partie,
        adversaire=adversaire,
        juridiction=juridiction,
    )
    click.echo(f"Bordereau généré : '{output}'.")


if __name__ == "__main__":
    cli()
