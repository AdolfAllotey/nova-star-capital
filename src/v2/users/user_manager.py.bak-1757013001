
# src/v2/users/user_manager.py

import json
import os

CONFIG_PATH = "src/v2/config/users.json"

def load_users():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"❌ Fichier utilisateur introuvable : {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        data = json.load(f)
    return data.get("users", [])

def get_user_by_id(user_id):
    users = load_users()
    for user in users:
        if user["id"] == user_id:
            return user
    return None

def list_user_ids():
    users = load_users()
    return [user["id"] for user in users]

def get_user_strategy(user_id):
    user = get_user_by_id(user_id)
    if user:
        return user.get("strategy", {})
    return {}

# Exemple d’utilisation
if __name__ == "__main__":
    print("👥 Utilisateurs disponibles :", list_user_ids())
    strategy = get_user_strategy("john_doe")
    print("📊 Stratégie de John :", strategy)
