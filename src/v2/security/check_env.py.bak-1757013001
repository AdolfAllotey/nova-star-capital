import os

required_vars = [
    "TELEGRAM_TOKEN",
    "ETHERSCAN_API_KEY",
    "INFURA_PROJECT_ID",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    # Ajoute ici toutes les variables nécessaires
]

def check_env_vars():
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"❌ Variables d'environnement manquantes : {', '.join(missing)}")
        return False
    print("✅ Toutes les variables d'environnement nécessaires sont définies.")
    return True

if __name__ == "__main__":
    check_env_vars()