import os
import pandas as pd
from datetime import datetime
from backtester import fetch_ohlcv
from backtester.macd_strategy import compute_macd_signals
from social.telegram_scraper import extract_tokens_from_csv
from social.reddit_scraper import extract_reddit_tokens

RESULT_DIR = "data/auto_trading"
os.makedirs(RESULT_DIR, exist_ok=True)

def simulate_macd_trading(symbol, start_date, end_date, timeframe="1h"):
    config = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "timeframe": timeframe,
    }

    try:
        df = fetch_ohlcv(config)
        if df.empty:
            print(f"⛔ Pas de données pour {symbol}")
            return None
    except Exception as e:
        print(f"❌ Erreur OHLCV {symbol}: {e}")
        return None

    try:
        df = compute_macd_signals(df)
    except Exception as e:
        print(f"❌ Erreur calcul MACD pour {symbol}: {e}")
        return None

    position = None
    entry_price = None
    trades = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if position is None and prev["macd"] < prev["macd_signal"] and row["macd"] > row["macd_signal"]:
            position = "long"
            entry_price = row["close"]
            entry_time = row["timestamp"]
        elif position == "long" and prev["macd"] > prev["macd_signal"] and row["macd"] < row["macd_signal"]:
            exit_price = row["close"]
            exit_time = row["timestamp"]
            pnl = (exit_price - entry_price) / entry_price * 100
            trades.append({
                "symbol": symbol,
                "entry_time": entry_time,
                "entry_price": entry_price,
                "exit_time": exit_time,
                "exit_price": exit_price,
                "return_pct": pnl
            })
            position = None
            entry_price = None

    if trades:
        df_trades = pd.DataFrame(trades)
        filename = os.path.join(RESULT_DIR, f"auto_macd_{symbol.replace('/', '')}.csv")
        df_trades.to_csv(filename, index=False)
        print(f"✅ Résultats sauvegardés : {filename}")
        return df_trades
    else:
        print(f"⚠️ Aucun trade exécuté pour {symbol}")
        return None

def run_auto_trading_macd():
    print("📂 Lancement auto-trading avec stratégie MACD...")
    start_date = "2024-01-01"
    end_date = "2024-05-01"

    print("📂 Chargement des fichiers...")
    telegram_tokens, reddit_tokens = [], []

    try:
        print("📥 Chargement Telegram...")
        telegram_tokens = extract_tokens_from_csv("data/social/telegram_messages_latest.csv")
        print(f"🟡 {len(telegram_tokens)} tokens depuis Telegram")
    except Exception as e:
        print(f"⚠️ Erreur Telegram : {e}")

    try:
        print("📥 Chargement Reddit...")
        reddit_tokens = extract_reddit_tokens("data/social/reddit_posts_latest.csv")
        print(f"🟡 {len(reddit_tokens)} tokens depuis Reddit")
    except Exception as e:
        print(f"⚠️ Erreur Reddit : {e}")

    all_tokens = list(set(telegram_tokens + reddit_tokens))
    print(f"✅ Tokens valides détectés : {all_tokens}")

    for token in all_tokens:
        symbol = token.replace("_KU", "/USDT") if "_KU" not in token else token
        simulate_macd_trading(symbol, start_date, end_date)

if __name__ == "__main__":
    run_auto_trading_macd()