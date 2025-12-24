import os
import sys
import pandas as pd
from datetime import datetime
import ccxt

# 🔧 Import interne
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backtester import fetch_ohlcv, export_results_to_csv
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.momentum_strategy import backtest_momentum_strategy
from backtester.export_results_to_csv import append_to_historique
from app_config.config_loader import load_config

# Charger les marchés Binance une seule fois
binance = ccxt.binance()
binance.load_markets()
binance_symbols = {m.split("/")[0] for m in binance.symbols if m.endswith("/USDT")}

def is_valid_binance_token(token):
    return token.upper() in binance_symbols

def extract_whale_tokens(csv_path, top_n=10):
    df = pd.read_csv(csv_path)
    if "token_symbol" not in df.columns:
        print("❌ Colonne 'token_symbol' introuvable.")
        return []

    tokens = df["token_symbol"].dropna().str.upper()
    valid = [t for t in tokens.unique() if is_valid_binance_token(t)]
    return valid[:top_n]

def run():
    print("🐋 Analyse des tokens extraits depuis les whales...")

    social_dir = "data/social"
    files = [f for f in os.listdir(social_dir) if f.startswith("whale_transactions") and f.endswith(".csv")]
    if not files:
        print("❌ Aucun fichier whale_transactions trouvé.")
        return

    latest_file = sorted(files)[-1]
    csv_path = os.path.join(social_dir, latest_file)

    tokens = extract_whale_tokens(csv_path, top_n=10)
    print(f"🔥 Tokens valides détectés : {tokens}")

    if not tokens:
        print("❌ Aucun token exploitable.")
        return

    for token in tokens:
        symbol = f"{token}/USDT"

        # --- Shitcoin ---
        config = load_config()
        config.update({"strategy": "shitcoin", "symbol": symbol})
        print(f"\n💣 Backtest SHITCOIN pour {symbol}")
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "whale_shitcoin", config)
            append_to_historique({
                "source": "Whale",
                "strategy": config["strategy"],
                "token": token,
                "timeframe": config.get("timeframe", "1h"),
                "start_date": config["start_date"],
                "end_date": config["end_date"],
                "return_pct": results["total_return_%"],
                "nb_trades": results["nb_trades"],
                "win_rate_pct": results["win_rate_%"]
            })
            print(f"✅ Shitcoin OK : {results['total_return_%']}%")
        except Exception as e:
            print(f"⛔ Shitcoin échoué pour {symbol} : {e}")

        # --- Momentum ---
        config = load_config()
        config.update({
            "strategy": "momentum",
            "symbol": symbol,
            "momentum_window": 3,
            "momentum_threshold_pct": 10.0
        })
        print(f"\n⚡ Backtest MOMENTUM pour {symbol}")
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_momentum_strategy(df, config)
            export_results_to_csv(df, "whale_momentum", config)
            append_to_historique({
                "source": "Whale",
                "strategy": config["strategy"],
                "token": token,
                "timeframe": config.get("timeframe", "1h"),
                "start_date": config["start_date"],
                "end_date": config["end_date"],
                "return_pct": results["total_return_%"],
                "nb_trades": results["nb_trades"],
                "win_rate_pct": results["win_rate_%"]
            })
            print(f"✅ Momentum OK : {results['total_return_%']}%")
        except Exception as e:
            print(f"⛔ Momentum échoué pour {symbol} : {e}")

if __name__ == "__main__":
    run()