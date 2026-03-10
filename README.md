# traitement-pdf

Outil Python en ligne de commande pour la gestion des pièces juridiques en PDF.

## Fonctionnalités

- **Découpage** d'un PDF selon son contenu (pages vides séparatrices, signets ou plages de pages)
- **Tamponnage** automatique de chaque pièce avec un tampon « Pièce N°X » visible sur chaque page
- **Numérotation** des pages (ex. « 1/3 ») apposée sur chaque page
- **Bordereau de communication des pièces** au format A4, avec tableau récapitulatif

## Installation

```bash
pip install -r requirements.txt
```

### Dépendances

| Paquet | Rôle |
|--------|------|
| `pypdf >= 3.0` | Lecture et manipulation de fichiers PDF |
| `reportlab >= 4.0` | Création de contenu PDF (tampon, bordereau) |
| `click >= 8.0` | Interface en ligne de commande |

## Utilisation

### Traitement complet (découpage + tamponnage + bordereau)

```bash
# Découpage par pages vides séparatrices (mode par défaut)
python main.py traiter document.pdf \
    --output-dir ./pieces \
    --titres "Contrat de bail" \
    --titres "Acte de naissance" \
    --titres "Correspondance" \
    --dossier "2024/001/TJ" \
    --partie "Maître Jean Dupont" \
    --adversaire "Maître Marie Martin" \
    --juridiction "Tribunal judiciaire de Paris"

# Découpage par plages de pages explicites
python main.py traiter document.pdf \
    --methode pages \
    --pages "1-5,6-12,13" \
    --titres "Contrat" \
    --titres "Bail" \
    --titres "Lettre"

# Découpage par signets (bookmarks) du PDF
python main.py traiter document.pdf --methode bookmarks
```

Le résultat est organisé dans le répertoire de sortie :
```
pieces/
├── split/          ← pièces découpées (avant tamponnage)
│   ├── piece_01.pdf
│   └── ...
├── stamped/        ← pièces tamponnées et numérotées
│   ├── piece_01.pdf
│   └── ...
└── bordereau.pdf   ← bordereau de communication
```

### Découpage seul

```bash
python main.py split document.pdf --methode blank --output-dir ./split
python main.py split document.pdf --methode pages --pages "1-3,4-6" --output-dir ./split
python main.py split document.pdf --methode bookmarks --output-dir ./split
```

### Tamponnage seul

```bash
python main.py stamp piece_01.pdf piece_02.pdf \
    --output-dir ./stamped \
    --titres "Contrat" \
    --titres "Acte"
```

### Bordereau seul

```bash
python main.py bordereau ./stamped \
    --output bordereau.pdf \
    --titres "Contrat" \
    --titres "Acte" \
    --dossier "2024/001" \
    --partie "Me Dupont" \
    --adversaire "Me Martin"
```

## Méthodes de découpage

| Méthode | Description |
|---------|-------------|
| `blank` | Utilise les pages vierges comme séparateurs entre les pièces |
| `pages` | Plages de pages fournies manuellement (ex. `"1-3,4-6,7"`) |
| `bookmarks` | Utilise les signets (outlines) de premier niveau du PDF |

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

