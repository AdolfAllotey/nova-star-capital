
# src/v2/utils/archive_utils.py

import os
import shutil
from datetime import datetime, timezone, timezone

def archive_session(files_to_save: dict, prefix: str = "session") -> str:
    """
    Archive les fichiers dans un sous-dossier horodaté.

    Args:
        files_to_save (dict): Clé = nom du fichier (ex: report.txt), valeur = chemin complet
        prefix (str): Préfixe du nom de dossier (ex: 'report', 'session')

    Returns:
        str: Chemin du dossier d’archive créé
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    archive_folder = f"data/v2/archive/{prefix}_{timestamp}"
    os.makedirs(archive_folder, exist_ok=True)

    for filename, source_path in files_to_save.items():
        if os.path.exists(source_path):
            shutil.copy(source_path, os.path.join(archive_folder, filename))
        else:
            print(f"⚠️ Fichier introuvable : {source_path}")

    print(f"📦 Fichiers archivés dans {archive_folder}")
    return archive_folder

# Exemple d'utilisation
if __name__ == "__main__":
    sample_files = {
        "report.txt": "data/v2/reports/latest_report.txt",
        "tokens.json": "data/v2/selection/selected_tokens.json"
    }
    archive_session(sample_files, prefix="test")
