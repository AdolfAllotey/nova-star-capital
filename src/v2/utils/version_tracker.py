# src/v2/utils/version_tracker.py

import os
import json
from datetime import datetime, timezone, timezone

VERSION_FILE = "data/v2/version_history.json"
os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)

def load_versions():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return json.load(f)
    else:
        return []

def save_versions(versions):
    with open(VERSION_FILE, "w") as f:
        json.dump(versions, f, indent=4)

def add_version(version_id, modules, author="Bot Crypto Ultra", notes=""):
    """
    Ajoute une nouvelle entrée de version.

    Args:
        version_id (str): Identifiant de la version (ex : 'V2.0.0').
        modules (list): Modules principaux inclus.
        author (str): Auteur ou responsable.
        notes (str): Commentaires ou changements apportés.
    """
    versions = load_versions()
    entry = {
        "version": version_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modules": modules,
        "author": author,
        "notes": notes
    }
    versions.append(entry)
    save_versions(versions)
    print(f"✅ Version {version_id} enregistrée.")

def list_versions():
    """
    Affiche l'historique des versions.
    """
    versions = load_versions()
    for entry in versions:
        print(f"📌 {entry['version']} | {entry['date']}")
        print(f"Modules : {', '.join(entry['modules'])}")
        print(f"Notes   : {entry['notes']}")
        print("-" * 40)

if __name__ == "__main__":
    # Exemple de test
    add_version(
        version_id="V2.0.0",
        modules=["main.py", "gain_protector.py", "llm_analyzer.py", "subaccount_tracker.py"],
        notes="Première mise en service complète de la V2 avec suivi des sous-comptes et analyse IA."
    )
    list_versions()