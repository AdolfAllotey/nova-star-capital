import os
import pandas as pd
from datetime import datetime

# Paramètres de simulation
INITIAL_PRICE = 1.0
SENTIMENT_IMPACT = {
    'bullish': 1.10,   # +10%
    'neutral': 1.00,   # 0%
    'bearish': 0.90    # -10%
}


def simulate_trade_result(sentiment):
    if sentiment > 0.2:
        return SENTIMENT_IMPACT['bullish']
    elif sentiment < -0.2:
        return SENTIMENT_IMPACT['bearish']
    else:
        return SENTIMENT_IMPACT['neutral']


def simulate_trades():
    print("\n📥 Lecture des fichiers de sentiment et de tokens...")
    tokens_path = "data/social/tokens_discovered_latest.csv"
    sentiment_path = "data/social/social_token_sentiment_latest.csv"

    if not os.path.exists(tokens_path) or not os.path.exists(sentiment_path):
        print("❌ Fichiers d’entrée manquants. Abandon de la simulation.")
        return

    df_tokens = pd.read_csv(tokens_path)
    df_sentiments = pd.read_csv(sentiment_path)

    print("🔗 Fusion des données sur les tokens et les sentiments...")
    df = pd.merge(df_tokens, df_sentiments, on="symbol", how="inner")

    print("🧮 Simulation des trades...")
    df["buy_price"] = INITIAL_PRICE
    df["sell_price"] = df["avg_sentiment"].apply(simulate_trade_result)
    df["gain"] = df["sell_price"] - df["buy_price"]
    df["gain_percent"] = (df["gain"] / df["buy_price"]) * 100

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "data/trading"
    os.makedirs(output_dir, exist_ok=True)

    # Fichier du jour
    daily_path = os.path.join(output_dir, f"simulated_trades_{timestamp}.csv")
    df.to_csv(daily_path, index=False)

    # Lien symbolique
    latest_symlink = os.path.join(output_dir, "simulated_trades_latest.csv")
    if os.path.exists(latest_symlink) or os.path.islink(latest_symlink):
        os.remove(latest_symlink)
    os.symlink(os.path.abspath(daily_path), latest_symlink)

    # Mise à jour du cumul
    global_path = os.path.join(output_dir, "simulated_trades_cumulative.csv")
    if os.path.exists(global_path):
        df_old = pd.read_csv(global_path)
        df_all = pd.concat([df_old, df], ignore_index=True)
    else:
        df_all = df.copy()
    df_all.to_csv(global_path, index=False)

    # Résumé
    total_gain = df["gain"].sum()
    avg_gain = df["gain_percent"].mean()
    print(f"\n✅ Simulation terminée : {len(df)} trades simulés")
    print(f"💰 Gain cumulé aujourd’hui : {total_gain:.2f} USDT")
    print(f"📈 Gain moyen : {avg_gain:.2f}%")
    print(f"📁 Fichier sauvegardé : {daily_path}")
    print(f"🔗 Lien symbolique mis à jour : {latest_symlink}")
    print(f"📊 Historique cumulatif mis à jour : {global_path}")


if __name__ == "__main__":
    simulate_trades()