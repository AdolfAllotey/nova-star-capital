
import os
import pandas as pd
import random
from datetime import datetime
from pathlib import Path

CAPITAL = 1000
STOP_LOSS = -0.10
TAKE_PROFIT = 0.10
SENTIMENT_MIN = 0.2
N_TOP_TOKENS = 10

def simulate_trade(price, stop_loss=STOP_LOSS, take_profit=TAKE_PROFIT):
    variation_pct = random.uniform(-0.15, 0.15)
    variation_pct = max(min(variation_pct, take_profit), stop_loss)
    sell_price = price * (1 + variation_pct)
    return sell_price, variation_pct

def run_simulation():
    score_path = "data/social/social_detected_tokens_ranked_latest.csv"
    sentiment_path = "data/social/social_token_sentiment_latest.csv"
    output_dir = Path("data/simulation/live")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(score_path) or not os.path.exists(sentiment_path):
        print("⚠️ Données manquantes.")
        return

    df_scores = pd.read_csv(score_path)
    df_sentiment = pd.read_csv(sentiment_path)

    df = pd.merge(df_scores, df_sentiment, how="inner", left_on="symbol", right_on="token")
    df = df[df["avg_sentiment"] >= SENTIMENT_MIN]
    df = df.sort_values(by="score", ascending=False).head(N_TOP_TOKENS).copy()

    df["weight"] = df["score"] * df["avg_sentiment"]
    df["weight_norm"] = df["weight"] / df["weight"].sum()
    df["allocated"] = df["weight_norm"] * CAPITAL

    results = []
    for _, row in df.iterrows():
        token = row["symbol"]
        sentiment = row["avg_sentiment"]
        base_price = random.uniform(0.01, 5.0)
        sell_price, pct = simulate_trade(base_price)
        invested = row["allocated"]
        quantity = invested / base_price
        final_value = quantity * sell_price
        profit = final_value - invested

        results.append({
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "token": token,
            "score": row["score"],
            "sentiment": round(sentiment, 3),
            "buy_price": round(base_price, 4),
            "sell_price": round(sell_price, 4),
            "variation_pct": round(pct * 100, 2),
            "profit": round(profit, 4),
            "invested": round(invested, 2)
        })

    df_result = pd.DataFrame(results)
    output_file = output_dir / "simulated_trades_live.csv"

    if output_file.exists():
        df_all = pd.read_csv(output_file)
        df_all = pd.concat([df_all, df_result], ignore_index=True)
    else:
        df_all = df_result

    df_all.to_csv(output_file, index=False)
    print(f"✅ Simulation live enregistrée à {output_file}")

if __name__ == "__main__":
    run_simulation()
