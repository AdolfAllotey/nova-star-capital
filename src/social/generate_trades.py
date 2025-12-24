# src/social/generate_trades.py

import os
import pandas as pd
from datetime import datetime
from pathlib import Path

TRADES_FOLDER = Path("data/trades")
TRADES_FOLDER.mkdir(parents=True, exist_ok=True)
CUMUL_PATH = TRADES_FOLDER / "trades_cumulative.csv"

def simulate_trades():
    print("📊 Simulation des trades...")

    # Charger scores & sentiments
    score_path = "data/social/social_detected_tokens_ranked_latest.csv"
    sentiment_path = "data/social/social_token_sentiment_latest.csv"
    df_scores = pd.read_csv(score_path)
    df_sentiments = pd.read_csv(sentiment_path)

    # Fusionner sur token
    df = pd.merge(df_scores, df_sentiments, how="inner", on="token")
    
    # Sélection stratégie : score ≥ 2 et avg_sentiment ≥ 0.1
    selected = df[(df["score"] >= 2) & (df["avg_sentiment"] >= 0.1)].copy()

    if selected.empty:
        print("⚠️ Aucun token sélectionné pour un trade simulé aujourd'hui.")
    else:
        print(f"✅ {len(selected)} trade(s) simulé(s) aujourd'hui.")

    # Simulation de prix d'achat/vente avec random ±5%
    import random
    selected["buy_price"] = [round(random.uniform(1, 5), 2) for _ in range(len(selected))]
    selected["sell_price"] = selected["buy_price"] * [random.uniform(0.95, 1.05) for _ in range(len(selected))]
    selected["sell_price"] = selected["sell_price"].round(2)
    selected["pnl"] = (selected["sell_price"] - selected["buy_price"]).round(2)

    selected["date"] = datetime.now().strftime("%Y-%m-%d")

    # Enregistrement du trade du jour
    today = datetime.now().strftime("%Y%m%d_%H%M%S")
    daily_path = TRADES_FOLDER / f"trades_simulated_{today}.csv"
    selected.to_csv(daily_path, index=False)

    # Mettre à jour cumul global
    if CUMUL_PATH.exists():
        df_cumul = pd.read_csv(CUMUL_PATH)
        df_all = pd.concat([df_cumul, selected], ignore_index=True)
    else:
        df_all = selected

    df_all.to_csv(CUMUL_PATH, index=False)

    # Rapport lisible (TXT)
    txt_path = TRADES_FOLDER / "trades_daily_report.txt"
    with open(txt_path, "w") as f:
        f.write(f"🧾 Rapport de simulation du {datetime.now().strftime('%Y-%m-%d')}\n\n")
        for _, row in selected.iterrows():
            f.write(f"- {row['token']} | Buy: {row['buy_price']} | Sell: {row['sell_price']} | PnL: {row['pnl']}\n")
        f.write(f"\nCumul total PnL: {df_all['pnl'].sum():.2f} USD\n")
    
    print(f"📄 Rapport TXT généré : {txt_path}")
    print(f"📦 Fichier trades simulés du jour : {daily_path}")
    print(f"📈 Cumul total des gains/pertes : {df_all['pnl'].sum():.2f} USD")

def main():
    simulate_trades()

__all__ = ["simulate_trades", "main"]

if __name__ == "__main__":
    main()