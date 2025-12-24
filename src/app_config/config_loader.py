import json
import os

def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app_config', 'config.json'))

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Fichier config.json non trouvé à : {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)