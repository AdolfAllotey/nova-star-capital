
import os
import json

CONFIG_PATH = "config/user_mode.json"
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

DEFAULT_CONFIG = {
    "mode": "single",  # ou "multi"
    "active_user": "default_user",
    "users": {
        "default_user": {
            "profile": "conservateur",
            "wallet": "0x123...",
            "exchange": "binance"
        }
    }
}

def load_user_mode():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_active_user_config():
    config = load_user_mode()
    mode = config.get("mode", "single")
    user_id = config.get("active_user", "default_user")
    user_data = config["users"].get(user_id, {})
    return mode, user_id, user_data

def switch_active_user(user_id):
    config = load_user_mode()
    if user_id in config["users"]:
        config["active_user"] = user_id
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        return True
    return False

if __name__ == "__main__":
    mode, uid, data = get_active_user_config()
    print(f"Mode actuel : {mode}")
    print(f"Utilisateur actif : {uid}")
    print(f"Données : {data}")
