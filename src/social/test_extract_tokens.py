import os
import glob
from social.telegram_scraper import extract_tokens_from_csv

# 🔍 Étape 1 : Trouver le fichier CSV le plus récent dans data/social/
csv_files = glob.glob("data/social/telegram_messages_*.csv")
if not csv_files:
    print("❌ Aucun fichier CSV trouvé dans data/social/")
else:
    latest_file = max(csv_files, key=os.path.getmtime)
    print(f"📂 Fichier analysé : {latest_file}")

    # 🔍 Étape 2 : Extraire les tokens les plus mentionnés
    tokens = extract_tokens_from_csv(latest_file, top_n=10)
    print("🔥 Tokens les plus mentionnés :", tokens)
