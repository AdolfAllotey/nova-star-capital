
import os
import dotenv
import pandas as pd
from datetime import datetime
from social.telegram_scraper import extract_tokens_from_csv
from social.reddit_scraper import extract_reddit_tokens
from utils.utils_volume import get_token_volume
from analytics.best_strategy_selector import best_strategy_per_token
from trading.simulate_strategy import simulate_strategy_on_token
from backtester.export_results_to_csv import append_to_historique
import requests

# === Load .env variables ===
dotenv.load_dotenv("run.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram config manquante")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

# === Paramètres ===
start_date = "2024-01-01"
end_date = datetime.now().strftime("%Y-%m-%d")
timeframe = "1h"
capital_per_token = 1000

# === Collecte des tokens ===
tg_tokens = extract_tokens_from_csv("data/social/telegram_messages_latest.csv")
rd_tokens = extract_reddit_tokens("data/social/reddit_posts_latest.csv")
all_tokens = list(set(tg_tokens + rd_tokens))
token_strategies = best_strategy_per_token()

daily_trades = []

# === Simulation ===
for token in all_tokens:
    strategy = token_strategies.get(token, "macd")
    symbol = token.replace("_KU", "/USDT") if "_KU" not in token else token

    try:
        df = simulate_strategy_on_token(token, strategy, start_date, end_date)
        if df and not df.empty:
            total_return = df["return_pct"].sum()
            nb_trades = len(df)
            pnl_usd = capital_per_token * total_return / 100

            # Alert instantanée
            message = f"""
🤖 *Trade simulé*

🪙 Token : {token}
📈 Stratégie : {strategy.upper()}
💰 PnL : {total_return:.2f}%
📊 Trades : {nb_trades}
📤 Capital alloué : ${capital_per_token:,.2f}
"""
            send_telegram_message(message)

            # Sauvegarde historique
            append_to_historique({
                "source": "Auto-Simu",
                "strategy": strategy,
                "token": token,
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "return_pct": total_return,
                "nb_trades": nb_trades,
                "win_rate_pct": None,
                "date_backtest": datetime.now().strftime("%Y-%m-%d")
            })

            daily_trades.append({
                "token": token,
                "strategy": strategy,
                "return_pct": total_return,
                "pnl_usd": pnl_usd
            })

    except Exception as e:
        print(f"❌ Erreur simulation {token}: {e}")

# === Récapitulatif du jour ===
if daily_trades:
    total_capital = capital_per_token * len(daily_trades)
    total_pnl = sum([t["pnl_usd"] for t in daily_trades])
    global_return = total_pnl / total_capital * 100 if total_capital else 0

    date = datetime.now().strftime("%Y-%m-%d")
    details = "\n".join([
        f"- {t['token']} → {t['strategy'].upper()} : {t['return_pct']:.2f}%"
        for t in daily_trades
    ])

    recap = f"""
🧾 *Résumé du jour*

📅 Date : {date}
💼 Capital investi : ${total_capital:,.2f}
📈 PnL total : ${total_pnl:,.2f}
📊 Rendement : {global_return:.2f}%

📄 *Détails :*
{details}
"""
    send_telegram_message(recap)
