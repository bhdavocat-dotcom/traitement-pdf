# traitement-pdf

Outil Python de traitement de pièces PDF destiné à la communication de documents (procédure judiciaire, dossier administratif, etc.).

## Fonctionnalités

- **Découpe** d'un fichier PDF source en pièces numérotées selon des plages de pages définies dans un fichier de configuration JSON
- **Tamponnement** de chaque page avec le numéro de pièce (« Pièce N° X ») et la pagination interne
- **Génération d'un bordereau de communication des pièces** (tableau récapitulatif au format PDF)

## Prérequis

- Python 3.9+
- Dépendances Python (voir `requirements.txt`) :

```bash
pip install -r requirements.txt
```

## Usage

### Avec fichier de configuration

```bash
python traitement_pdf.py document.pdf --config config.json --output dossier_sortie/
```

### Sans configuration (pièce unique)

```bash
python traitement_pdf.py document.pdf --output dossier_sortie/
```

Le PDF est traité comme une seule pièce.

## Format du fichier de configuration

```json
{
    "titre_bordereau": "BORDEREAU DE COMMUNICATION DES PIÈCES",
    "pieces": [
        {
            "titre": "Contrat principal",
            "page_debut": 1,
            "page_fin": 3
        },
        {
            "titre": "Annexe 1 - Conditions générales",
            "page_debut": 4,
            "page_fin": 6
        }
    ]
}
```

Un exemple est fourni dans le fichier `config_exemple.json`.

## Fichiers générés

Dans le répertoire de sortie :

| Fichier | Description |
|---|---|
| `piece_01_<titre>.pdf` | Première pièce tamponnée |
| `piece_02_<titre>.pdf` | Deuxième pièce tamponnée |
| … | … |
| `bordereau.pdf` | Bordereau de communication des pièces |

## Tests

```bash
python -m pytest tests/ -v
```
