import os
import sys
from datetime import datetime
import ccxt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from backtester import fetch_ohlcv, export_results_to_csv
from shitcoin_strategy import backtest_shitcoin_strategy
from backtester.export_results_to_csv import append_to_historique  # ✅ AJOUT
from app_config.config_loader import load_config
from social.reddit_scraper import extract_reddit_tokens

# Initialise Binance
binance = ccxt.binance()

STOP_WORDS = {
    "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT", "IS", "ON", "TO",
    "IN", "OF", "YOU", "YOUR", "IT", "A", "AS", "AT", "BY"
}

def is_valid_symbol(token):
    if len(token) < 3 or token.upper() in STOP_WORDS:
        return False
    try:
        market = binance.market(f"{token}/USDT")
        return market is not None
    except Exception:
        return False

def run():
    print("👽 Analyse des tokens extraits depuis Reddit...")

    social_dir = "data/social"
    files = [f for f in os.listdir(social_dir) if f.startswith("reddit_posts_")]
    if not files:
        print("❌ Aucun fichier Reddit trouvé.")
        return

    latest_file = sorted(files)[-1]
    csv_path = os.path.join(social_dir, latest_file)

    print(f"📂 Fichier analysé : {csv_path}")
    tokens = extract_reddit_tokens(csv_path, top_n=10)
    filtered_tokens = [t for t in tokens if is_valid_symbol(t)]
    print(f"🔥 Tokens valides à backtester : {filtered_tokens}")

    if not filtered_tokens:
        print("❌ Aucun token valide détecté.")
        return

    config = load_config()
    config["strategy"] = "shitcoin"

    for token in filtered_tokens:
        symbol = f"{token}/USDT"
        print(f"\n🔍 Tentative de backtest pour {symbol}...")

        config["symbol"] = symbol
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "reddit_shitcoin", config)

            print(f"✅ {symbol} : {results['total_return_%']}% | Trades : {results['nb_trades']} | Win rate : {results['win_rate_%']}%")

            # ✅ ENREGISTREMENT HISTORIQUE
            append_to_historique({
                "source": "Reddit",
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