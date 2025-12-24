import os
from social.telegram_scraper import extract_tokens_from_csv

# ➤ Chemin vers le dernier fichier CSV généré par telegram_scraper
latest_csv = "data/social/telegram_messages_20250507_233651.csv"  # ⚠️ Remplace par le nom exact si besoin

# ➤ Nombre de tokens les plus fréquents à extraire
top_n = 10

# ➤ Exécution du test
print("🧪 Test d'extraction de tokens depuis Telegram...")
top_tokens = extract_tokens_from_csv(latest_csv, top_n=top_n)
print("✅ Résultat :", top_tokens)