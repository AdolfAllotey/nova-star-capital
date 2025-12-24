import os
import sys

# Ajouter le chemin du dossier src pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from social.telegram_scraper_list_groups import fetch_user_groups

if __name__ == "__main__":
    print("🔍 Récupération des groupes Telegram...")
    groups = fetch_user_groups()
    print(f"✅ {len(groups)} groupes trouvés.")
    print("📋 Liste des groupes :")
    for group in groups:
        print("-", group)
