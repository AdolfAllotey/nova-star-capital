import pandas as pd
import re
import os
from collections import Counter
from datetime import datetime

DATA_DIR = "data/social"

def extract_token_mentions(text):
    """
    Extrait les tokens précédés de $ ou des mots majuscules courts (souvent utilisés comme tickers).
    """
    cashtags = re.findall(r"\$[A-Z]{2,10}", text)
    uppercase_words = re.findall(r"\b[A-Z]{2,6}\b", text)
    return cashtags + uppercase_words

def extract_top_tokens_from_telegram_csv(n=10):
    """
    Analyse le fichier Telegram le plus récent et retourne les tokens les plus fréquents.
    """
    if not os.path.exists(DATA_DIR):
        print("❌ Dossier data/social introuvable.")
        return []

    # Trouver le fichier le plus récent
    files = sorted([
        os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
        if f.startswith("telegram_messages_") and f.endswith(".csv")
    ])

    if not files:
        print("❌ Aucun fichier Telegram trouvé.")
        return []

    latest_file = files[-1]
    df = pd.read_csv(latest_file)

    all_tokens = []
    for msg in df["message"].dropna():
        all_tokens.extend(extract_token_mentions(msg))

    counter = Counter([t.replace("$", "") for t in all_tokens])
    top = counter.most_common(n)

    print("\n🔥 Tokens les plus mentionnés dans Telegram :")
    for token, count in top:
        print(f"{token}: {count} mentions")

    return [token for token, _ in top]

if __name__ == "__main__":
    extract_top_tokens_from_telegram_csv()