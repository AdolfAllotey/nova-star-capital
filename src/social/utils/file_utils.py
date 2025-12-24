import os
import pandas as pd
from datetime import datetime

def save_dataframe_with_timestamp(df, base_filename="data", folder="data", latest_symlink=False):
    # Création du dossier cible
    os.makedirs(folder, exist_ok=True)

    # Nom horodaté du fichier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_filename}_{timestamp}.csv"
    filepath = os.path.join(folder, filename)

    # Sauvegarde CSV
    df.to_csv(filepath, index=False)

    # Symlink optionnel vers la dernière version
    if latest_symlink:
        symlink_path = os.path.join(folder, f"{base_filename}_latest.csv")
        if os.path.islink(symlink_path) or os.path.exists(symlink_path):
            os.remove(symlink_path)
        os.symlink(filename, symlink_path)