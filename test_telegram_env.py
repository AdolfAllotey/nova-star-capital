import os
from dotenv import load_dotenv

# Charger les variables depuis le fichier telegram.env
dotenv_path = os.path.join(os.path.dirname(__file__), 'telegram.env')
load_dotenv(dotenv_path)

# Lire les valeurs
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

# Vérifier si elles sont bien chargées
if api_id and api_hash:
    print("✅ Variables chargées avec succès :")
    print(f"API ID    : {api_id}")
    print(f"API Hash  : {api_hash}")
else:
    print("❌ Erreur : Impossible de charger TELEGRAM_API_ID ou TELEGRAM_API_HASH. Vérifie le fichier telegram.env.")
