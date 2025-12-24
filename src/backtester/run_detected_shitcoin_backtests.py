import os
import sys
from datetime import datetime
import pandas as pd

# 🔧 Ajout du dossier src au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from detect_hot_tokens import detect_hot_usdt_pairs
from backtester.backtester import fetch_ohlcv, export_results_to_csv
from shitcoin_strategy import backtest_shitcoin_strategy
from app_config.config_loader import load_config

def run():
    print("🔍 Scan des paires en pump...")
    hot_pairs = detect_hot_usdt_pairs()
    print(f"📊 {len(hot_pairs)} paire(s) détectée(s)")

    if not hot_pairs:
        return

    config = load_config()
    config["strategy"] = "shitcoin"
    summary_rows = []

    for pair in hot_pairs:
        symbol = pair["symbol"]
        print(f"\n▶️ Backtest de {symbol}...")

        config["symbol"] = symbol
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "shitcoin", config)

            print(f"✅ {symbol} : {results['total_return_%']}% | Trades : {results['nb_trades']} | Win rate : {results['win_rate_%']}%")

            summary_rows.append({
                "symbol": symbol,
                "total_return_%": results['total_return_%'],
                "nb_trades": results['nb_trades'],
                "win_rate_%": results['win_rate_%'],
                "date": datetime.now().strftime("%Y-%m-%d")
            })

        except Exception as e:
            print(f"❌ Erreur sur {symbol} : {e}")

    if summary_rows:
        df_summary = pd.DataFrame(summary_rows)
        os.makedirs("data/results", exist_ok=True)
        df_summary.to_csv("data/results/shitcoin_batch_summary.csv", index=False)
        print("\n📊 Résumé exporté dans : data/results/shitcoin_batch_summary.csv")

if __name__ == "__main__":
    run()