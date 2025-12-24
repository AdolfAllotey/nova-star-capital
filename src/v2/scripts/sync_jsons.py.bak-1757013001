import os
import shutil

# Répertoire source : où le bot V1 génère les JSON (à adapter si besoin)
SOURCE_FOLDER = "src/v2/data/simulation/"
DEST_FOLDER = "src/v2/public/data/simulation/"

# Crée le dossier destination s'il n'existe pas
os.makedirs(DEST_FOLDER, exist_ok=True)

# Liste les fichiers JSON dans le dossier source
for filename in os.listdir(SOURCE_FOLDER):
    if filename.endswith(".json"):
        src_path = os.path.join(SOURCE_FOLDER, filename)
        dest_path = os.path.join(DEST_FOLDER, filename)
        shutil.copy2(src_path, dest_path)
        print(f"✅ {filename} synchronisé vers React public/")