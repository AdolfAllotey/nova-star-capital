
# src/v2/core/access_control.py

import json
import os

ACCESS_FILE = "src/v2/config/user_roles.json"

# Valeurs possibles : admin, user, readonly, test
def load_roles():
    if not os.path.exists(ACCESS_FILE):
        return {}
    with open(ACCESS_FILE, "r") as f:
        return json.load(f)

def get_role(user_id):
    roles = load_roles()
    return roles.get(user_id, "user")  # Par défaut "user"

def is_admin(user_id):
    return get_role(user_id) == "admin"

def can_edit(user_id):
    return get_role(user_id) in ["admin", "user"]

def is_readonly(user_id):
    return get_role(user_id) in ["readonly", "test"]
