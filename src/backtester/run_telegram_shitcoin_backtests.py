import os
import sys
from datetime import datetime

# 🔧 Ajout du dossier 'src' au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backtester.backtester import fetch_ohlcv, export_results_to_csv
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from social.telegram_scraper import extract_tokens_from_csv
from app_config.config_loader import load_config

def run():
    print("📨 Analyse des tokens détectés dans Telegram...")

    # 🗂️ Chemin vers le dernier fichier Telegram
    telegram_dir = "data/social"
    files = [f for f in os.listdir(telegram_dir) if f.startswith("telegram_messages_") and f.endswith(".csv")]
    if not files:
        print("❌ Aucun fichier Telegram trouvé.")
        return

    latest_file = sorted(files)[-1]
    csv_path = os.path.join(telegram_dir, latest_file)

    tokens = extract_tokens_from_csv(csv_path, top_n=10)
    print(f"🔍 {len(tokens)} token(s) à backtester...")

    config = load_config()
    config["strategy"] = "telegram"

    for token in tokens:
        symbol = f"{token}/USDT"
        print(f"\n🔍 Tentative de backtest pour {symbol}...")

        config["symbol"] = symbol
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "telegram", config)

            print(f"✅ {symbol} : {results['total_return_%']}% | Trades : {results['nb_trades']} | Win rate : {results['win_rate_%']}%")
        except Exception as e:
            print(f"⛔ {symbol} échoué : {e}")

if __name__ == "__main__":
    run()