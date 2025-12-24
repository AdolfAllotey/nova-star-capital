import json
import os

def load_email_config(path="config.json"):
    """
    Charge les paramètres email à partir d'un fichier JSON.
    Si le fichier n'existe pas ou une clé est absente, lève une erreur.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Le fichier de configuration '{path}' est introuvable.")

    with open(path, "r") as f:
        config = json.load(f)

    if "email" not in config:
        raise KeyError("Clé 'email' manquante dans le fichier de configuration.")

    email_config = config["email"]
    required_keys = ["smtp_server", "smtp_port", "login", "password"]

    for key in required_keys:
        if key not in email_config:
            raise KeyError(f"Clé '{key}' manquante dans la configuration email.")

    return email_config