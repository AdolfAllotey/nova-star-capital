import os
import json
import random
from datetime import datetime
import pandas as pd

from src.utils.token_utils import get_top_scored_tokens
from src.utils.file_utils import save_json_with_timestamp

# Ajout pour Telegram
from src.utils.telegram_bot import send_telegram_message

# Paramètres
MIN_SENTIMENT = 0.2
STOP_LOSS = -0.10
TAKE_PROFIT = 0.30
BASE_INVESTMENT = 100  # montant de base simulé

# Chemins
REPORT_FOLDER = "data/trades"
SIMULATION_FOLDER = "data/simulation"

os.makedirs(REPORT_FOLDER, exist_ok=True)
os.makedirs(SIMULATION_FOLDER, exist_ok=True)

def simulate_trades():
    today = datetime.today().strftime("%Y-%m-%d")
    tokens = get_top_scored_tokens()
    selected = []

    for token in tokens:
        sentiment = token.get("sentiment", 0)
        score = token.get("score", 0)

        if sentiment < MIN_SENTIMENT:
            continue

        # pondération : plus le sentiment est élevé, plus le montant investi est important
        amount = BASE_INVESTMENT * (0.5 + sentiment + score)

        entry_price = random.uniform(0.9, 1.1) * token.get("price", 1)
        change_pct = random.uniform(-0.2, 0.4)  # -20% à +40%
        exit_price = entry_price * (1 + change_pct)

        gain_pct = (exit_price - entry_price) / entry_price
        if gain_pct <= STOP_LOSS:
            gain_pct = STOP_LOSS
            exit_price = entry_price * (1 + STOP_LOSS)
        elif gain_pct >= TAKE_PROFIT:
            gain_pct = TAKE_PROFIT
            exit_price = entry_price * (1 + TAKE_PROFIT)

        result = {
            "token": token["symbol"],
            "sentiment": round(sentiment, 3),
            "score": round(score, 3),
            "amount": round(amount, 2),
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "gain_pct": round(gain_pct * 100, 2),
            "date": today
        }
        selected.append(result)

    return selected

def save_results(trades):
    today = datetime.today().strftime("%Y-%m-%d")
    if not trades:
        return

    df = pd.DataFrame(trades)
    df.to_csv(os.path.join(REPORT_FOLDER, "trades_simulated_all.csv"), mode="a", header=not os.path.exists(os.path.join(REPORT_FOLDER, "trades_simulated_all.csv")), index=False)
    df.to_csv(os.path.join(SIMULATION_FOLDER, f"trades_{today.replace('-', '')}.json"), index=False)

    latest_text = "\n".join([
        f"{t['token']} | Sentiment: {t['sentiment']} | Gain: {t['gain_pct']}% | Entry: {t['entry_price']} | Exit: {t['exit_price']}"
        for t in trades
    ])
    with open(os.path.join(REPORT_FOLDER, "trades_simulated_latest.txt"), "w") as f:
        f.write(latest_text)

    with open(os.path.join(REPORT_FOLDER, "trades_daily_report.txt"), "w") as f:
        f.write("Rapport quotidien de simulation des trades\n\n")
        f.write(latest_text)

    print(f"✅ Rapport sauvegardé dans : {os.path.join(REPORT_FOLDER, 'trades_daily_report.txt')}")

    # Envoi Telegram
    send_telegram_message(f"\ud83d\udcca *Simulation quotidienne des trades :*\n\n{latest_text}", parse_mode="Markdown")

def main():
    trades = simulate_trades()
    if trades:
        save_results(trades)
    else:
        print("Aucun trade simulé aujourd'hui.")

if __name__ == "__main__":
    main()
