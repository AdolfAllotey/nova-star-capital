import pandas as pd
from social.telegram_scraper import extract_tokens_from_csv
from social.reddit_scraper import extract_reddit_tokens

print("==== ✅ Lancement des tests Social Scrapers ====\n")

# Test pour Telegram
try:
    df = extract_tokens_from_csv("data/social/telegram_tokens.csv")
    assert isinstance(df, pd.DataFrame), "Le résultat n'est pas un DataFrame"
    assert not df.empty, "Le DataFrame Telegram est vide"
    print("✅ Telegram : extraction réussie")
except FileNotFoundError:
    print("❌ Fichier introuvable : data/social/telegram_tokens.csv")
except AssertionError as e:
    print(f"❌ Telegram : {e}")
except Exception as e:
    print(f"❌ Telegram : Erreur inattendue - {e}")

print("\n---------------------------------\n")

# Test pour Reddit
try:
    df = extract_reddit_tokens("data/social/reddit_tokens.csv")
    assert isinstance(df, pd.DataFrame), "Le résultat n'est pas un DataFrame"
    assert not df.empty, "Le DataFrame Reddit est vide"
    print("✅ Reddit : extraction réussie")
except FileNotFoundError:
    print("❌ Fichier introuvable : data/social/reddit_tokens.csv")
except AssertionError as e:
    print(f"❌ Reddit : {e}")
except Exception as e:
    print(f"❌ Reddit : Erreur inattendue - {e}")

print("\n==== 🧪 Fin des tests ====")