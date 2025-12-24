# src/simulation/generate_trade.py

import os
import pandas as pd
from datetime import datetime
import random

SCORES_PATH = "data/social/social_detected_tokens_ranked_latest.csv"
SENTIMENT_PATH = "data/social/social_token_sentiment_latest.csv"
TRADES_DIR = "data/simulation"
CUMUL_PATH = os.path.join(TRADES_DIR, "simulated_cumulative_pnl.csv")

def simulate_price():
    """Simule un prix d'achat et un prix de vente avec un gain ou perte entre -10% et +10%"""
    buy_price = round(random.uniform(0.01, 2.0), 4)
    variation_pct = random.uniform(-0.10, 0.10)
    sell_price = round(buy_price * (1 + variation_pct), 4)
    return buy_price, sell_price, variation_pct

def main():
    print("📊 Simulation des trades...")

    # Chargement des données
    if not os.path.exists(SCORES_PATH) or not os.path.exists(SENTIMENT_PATH):
        print("❌ Données de score ou sentiment manquantes.")
        return

    df_scores = pd.read_csv(SCORES_PATH)
    df_sentiments = pd.read_csv(SENTIMENT_PATH)

    # Merge sur token
    df = pd.merge(df_scores, df_sentiments, how="inner", left_on="symbol", right_on="token")
    df["score_sentiment"] = df["score"] * df["avg_sentiment"]

    # Filtrer les tokens avec un score * sentiment > seuil
    selected = df[df["score_sentiment"] > 0.5].copy()

    if selected.empty:
        print("❌ Aucun token retenu pour simulation aujourd'hui.")
        return

    trades = []
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    for _, row in selected.iterrows():
        buy_price, sell_price, pct = simulate_price()
        gain = sell_price - buy_price
        trades.append({
            "date": date_str,
            "token": row["symbol"],
            "score": row["score"],
            "avg_sentiment": round(row["avg_sentiment"], 4),
            "buy_price": buy_price,
            "sell_price": sell_price,
            "pnl": round(gain, 4),
            "variation_%": round(pct * 100, 2)
        })

    df_trades = pd.DataFrame(trades)

    # Sauvegarde journalière
    os.makedirs(TRADES_DIR, exist_ok=True)
    filename = f"simulated_trades_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    daily_path = os.path.join(TRADES_DIR, filename)
    df_trades.to_csv(daily_path, index=False)
    print(f"✅ {len(df_trades)} trade(s) simulé(s) sauvegardé(s) dans {daily_path}")

    # Cumul global
    if os.path.exists(CUMUL_PATH):
        df_cumul = pd.read_csv(CUMUL_PATH)
        df_cumul = pd.concat([df_cumul, df_trades], ignore_index=True)
    else:
        df_cumul = df_trades.copy()

    df_cumul.to_csv(CUMUL_PATH, index=False)
    print(f"📈 Cumul total des trades simulés mis à jour dans {CUMUL_PATH}")
    print(f"💰 PnL cumulé : {df_cumul['pnl'].sum():.4f} USDT (simulé)")

if __name__ == "__main__":
    main()