# Photo Organizer

Application desktop pour Windows permettant de classer des photos depuis un répertoire source vers un répertoire destination. Les fichiers sont copiés dans des dossiers datés (AAAA-MM-JJ) en utilisant la date de prise de vue EXIF lorsqu'elle est disponible, sinon la date du fichier.

## Fonctionnalités principales
- Sélection d'un dossier source et d'un dossier destination.
- Détection automatique des images (JPG, PNG, HEIC, TIFF, BMP).
- Prévisualisation des images avec choix rapide de l'action :
  - **Copy** : copie dans le dossier destination (sous-dossier daté).
  - **Skip** : ignore le fichier.
  - **Delete** : supprime le fichier dans le dossier source.
- Barre d'état indiquant la progression des opérations.

## Prérequis
- Windows avec Python 3.10+.
- Dépendances Python : [Pillow](https://python-pillow.org/) (voir `requirements.txt`).
- Tkinter est fourni avec les distributions officielles de Python sous Windows.

## Installation
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Utilisation
```bash
python photo_organizer.py
```

1. Cliquez sur **Choose** pour sélectionner le dossier source contenant les photos.
2. Cliquez sur **Choose** pour définir le dossier destination.
3. Sélectionnez une photo dans la liste pour l'afficher en aperçu.
4. Choisissez l'action (Copy / Skip / Delete) pour la photo sélectionnée.
5. Quand tout est prêt, cliquez sur **Process files** pour lancer le traitement.

Les photos copiées seront rangées dans des sous-dossiers nommés par date (ex : `2024-03-18`).

## Remarques
- La suppression est définitive : confirmez l'alerte avant de continuer.
- En l'absence de métadonnées EXIF (DateTimeOriginal ou DateTime), la date de modification du fichier est utilisée.
