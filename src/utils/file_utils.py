import json
import os
from datetime import datetime

def save_json_with_timestamp(data, folder, prefix):
    """
    Sauvegarde un dictionnaire JSON dans un dossier donné,
    avec un nom de fichier basé sur la date et un préfixe.
    """
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(folder, filename)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return filepath