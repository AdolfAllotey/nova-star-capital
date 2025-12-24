import os
import sys
import pandas as pd
from datetime import datetime

# Ajouter src/ au chemin pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backtester import fetch_ohlcv, export_results_to_csv
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.export_results_to_csv import append_to_historique  # ✅ AJOUT
from app_config.config_loader import load_config

def extract_whale_tokens(csv_path, top_n=10):
    df = pd.read_csv(csv_path)
    if "token_symbol" not in df.columns:
        print("❌ Colonne 'token_symbol' introuvable.")
        return []
    tokens = df["token_symbol"].value_counts().head(top_n).index.tolist()
    return tokens

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
    print(f"🔥 Tokens détectés : {tokens}")

    if not tokens:
        print("❌ Aucun token détecté.")
        return

    config = load_config()
    config["strategy"] = "shitcoin"

    for token in tokens:
        symbol = f"{token}/USDT"
        print(f"\n🔍 Tentative de backtest pour {symbol}...")

        config["symbol"] = symbol
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "whale_shitcoin", config)

            print(f"✅ {symbol} : {results['total_return_%']}% | Trades : {results['nb_trades']} | Win rate : {results['win_rate_%']}%")

            # ✅ ENREGISTREMENT HISTORIQUE
            append_to_historique({
                "source": "Whale",
                "strategy": config["strategy"],
                "token": config["symbol"],
                "timeframe": config.get("timeframe", "1h"),
                "start_date": config["start_date"],
                "end_date": config["end_date"],
                "return_pct": results["total_return_%"],
                "nb_trades": results["nb_trades"],
                "win_rate_pct": results["win_rate_%"]
            })

        except Exception as e:
            print(f"⛔ {symbol} échoué : {e}")

if __name__ == "__main__":
    run()