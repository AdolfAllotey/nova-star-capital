import os
import sys
import pandas as pd
from datetime import datetime
from collections import Counter

# 🔧 Ajout du chemin pour les imports relatifs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_config.config_loader import load_config
from backtester import fetch_ohlcv, export_results_to_csv
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.export_results_to_csv import append_to_historique
from social.twitter_scraper import detect_trending_tokens

def run():
    print("📨 Analyse des tokens extraits depuis Twitter...")

    # 🔍 Extraction des tokens via le scraper (avec cache)
    tokens = detect_trending_tokens()
    if not tokens:
        print("❌ Aucun token détecté.")
        return

    if isinstance(tokens, list):
        token_list = [t[0] if isinstance(t, tuple) else t for t in tokens]
    else:
        print("❌ Format inattendu de la liste de tokens.")
        return

    print(f"🔥 Tokens valides détectés : {token_list}")

    # 🔁 Backtests pour chaque token
    for token in token_list:
        symbol = f"{token}/USDT"

        config = load_config()
        config.update({
            "strategy": "shitcoin",
            "symbol": symbol
        })

        print(f"💣 Backtest SHITCOIN pour {symbol}")
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "twitter_shitcoin", config)

            append_to_historique({
                "source": "Twitter",
                "strategy": config["strategy"],
                "token": token,
                "timeframe": config.get("timeframe", "1h"),
                "start_date": config["start_date"],
                "end_date": config["end_date"],
                "return_pct": results["total_return_%"],
                "nb_trades": results["nb_trades"],
                "win_rate_pct": results["win_rate_%"]
            })

            print(f"✅ Résultat OK : {results['total_return_%']}%")
        except Exception as e:
            print(f"⛔ Échec pour {symbol} : {e}")

if __name__ == "__main__":
    run()