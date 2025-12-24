
# Profils de stratégie utilisateur : chaque profil définit un style d’allocation et de risque.

STRATEGY_PROFILES = {
    "prudent": {
        "name": "prudent",
        "risk_level": "low",
        "allocation_multiplier": 0.5,
        "description": "Conservateur, avec capital majoritairement en sécurité."
    },
    "equilibre": {
        "name": "equilibre",
        "risk_level": "medium",
        "allocation_multiplier": 1.0,
        "description": "Répartition équilibrée entre trading et sécurité."
    },
    "agressif": {
        "name": "agressif",
        "risk_level": "high",
        "allocation_multiplier": 1.5,
        "description": "Priorité au rendement, avec exposition élevée au risque."
    }
}

def get_profile(name: str):
    return STRATEGY_PROFILES.get(name.lower())

def list_profiles():
    return list(STRATEGY_PROFILES.keys())

# Exemple d'utilisation
if __name__ == "__main__":
    for name in list_profiles():
        profile = get_profile(name)
        print(f"{name.upper()} : {profile['description']} (x{profile['allocation_multiplier']})")
