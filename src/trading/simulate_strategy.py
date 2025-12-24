import os
import json
import pandas as pd
from datetime import datetime
from backtester import fetch_ohlcv
from backtester.macd_strategy import compute_macd_signals
from backtester.rsi_strategy import compute_rsi_signals
from backtester.ema_strategy import compute_ema_signals
from backtester.momentum_strategy import compute_momentum_signals

def simulate_strategy_on_token(token, strategy="macd", start_date="2024-01-01", end_date="2024-05-01", timeframe="1h", stop_loss_pct=0, trailing_stop_pct=0):
    base_token = token.replace("_KU", "")
    symbol = f"{base_token}/USDT"

    config = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "timeframe": timeframe,
        "momentum_window": 3,
        "momentum_threshold_pct": 10
    }

    try:
        df = fetch_ohlcv(config)
        if df is None or df.empty:
            return {"token": token, "status": "no_data", "return_pct": 0, "nb_trades": 0}

        if strategy == "macd":
            df = compute_macd_signals(df)
        elif strategy == "rsi":
            df = compute_rsi_signals(df)
        elif strategy == "ema":
            df = compute_ema_signals(df)
        elif strategy == "momentum":
            df = compute_momentum_signals(df, config)
        else:
            return {"token": token, "status": "invalid_strategy", "return_pct": 0, "nb_trades": 0}

        trades = []
        position = None
        entry_price = None
        entry_time = None
        highest_price = None

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]

            signal_entry = False
            signal_exit = False

            if strategy == "macd":
                signal_entry = prev["macd"] < prev["macd_signal"] and row["macd"] > row["macd_signal"]
                signal_exit = prev["macd"] > prev["macd_signal"] and row["macd"] < row["macd_signal"]
            elif strategy == "rsi":
                signal_entry = prev["rsi"] < 30 and row["rsi"] > 30
                signal_exit = prev["rsi"] > 70 and row["rsi"] < 70
            elif strategy == "ema":
                signal_entry = prev["ema_short"] < prev["ema_long"] and row["ema_short"] > row["ema_long"]
                signal_exit = prev["ema_short"] > prev["ema_long"] and row["ema_short"] < row["ema_long"]
            elif strategy == "momentum":
                signal_entry = row.get("signal") == "buy"
                signal_exit = row.get("signal") == "sell"

            if position is None and signal_entry:
                position = "long"
                entry_price = row["close"]
                entry_time = row["timestamp"]
                highest_price = row["close"]
            elif position == "long":
                highest_price = max(highest_price, row["close"])
                current_return = (row["close"] - entry_price) / entry_price * 100

                if stop_loss_pct and current_return <= -stop_loss_pct:
                    signal_exit = True

                if trailing_stop_pct:
                    trailing_stop_price = highest_price * (1 - trailing_stop_pct / 100)
                    if row["close"] < trailing_stop_price:
                        signal_exit = True

                if signal_exit:
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
            return {
                "token": token,
                "status": "ok",
                "return_pct": round(df_trades["return_pct"].sum(), 2),
                "nb_trades": len(df_trades)
            }
        else:
            return {"token": token, "status": "no_trades", "return_pct": 0, "nb_trades": 0}

    except Exception as e:
        print(f"Erreur dans simulate_strategy_on_token pour {token} : {e}")
        return {
            "token": token,
            "status": "error",
            "error": str(e),
            "return_pct": 0,
            "nb_trades": 0
        }

# === Point d’entrée pour le bot ===
def main():
    tokens = ["BTC", "ETH", "XRP"]
    results = []

    for token in tokens:
        result = simulate_strategy_on_token(token, strategy="macd")
        print(f"{token} → {result['status']} | {result['return_pct']}% sur {result['nb_trades']} trades")
        results.append(result)

    # Sauvegarde des résultats
    today = datetime.now().strftime("%Y%m%d")
    os.makedirs("data/simulation/", exist_ok=True)
    file_path = f"data/simulation/trades_{today}.json"
    with open(file_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"📁 Résultats enregistrés dans {file_path}")

if __name__ == "__main__":
    main()