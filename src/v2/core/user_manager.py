
# src/v2/core/user_manager.py

import json
import os

CONFIG_PATH = "src/v2/config/user_profiles.json"

def load_user_profile(profile_name="default"):
    """
    Charge le profil utilisateur depuis le fichier JSON.

    Args:
        profile_name (str): Nom du profil à charger.

    Returns:
        dict: Dictionnaire des paramètres du profil.
    """
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"❌ Fichier de profils introuvable à {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as f:
        profiles = json.load(f)

    if profile_name not in profiles:
        raise ValueError(f"❌ Profil '{profile_name}' non trouvé dans user_profiles.json")

    return profiles[profile_name]

# Exemple de test
if __name__ == "__main__":
    profile = load_user_profile("default")
    print("Profil chargé :", profile)
