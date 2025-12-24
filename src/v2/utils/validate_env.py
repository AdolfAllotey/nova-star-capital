
from src.v2.utils.config_loader import load_config

def validate_config(required_keys=None):
    if required_keys is None:
        required_keys = {
            "telegram": ["api_key", "chat_id"],
            "binance": ["api_key", "api_secret"],
            "llm": ["api_key"]
        }

    config = load_config()
    missing = {}

    for section, keys in required_keys.items():
        if section not in config:
            missing[section] = "Section manquante"
            continue
        for key in keys:
            if key not in config[section]:
                missing.setdefault(section, []).append(key)

    if missing:
        raise ValueError(f"Clés de configuration manquantes : {missing}")
    return True

# Exemple :
# validate_config()  # lève une erreur si une clé est manquante
