import os
from datetime import datetime
from backtester import fetch_ohlcv, export_results_to_csv
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from app_config.config_loader import load_config
from social.telegram_scraper import extract_tokens_from_csv
from backtester.export_results_to_csv import append_to_historique  # ✅ NOUVEL IMPORT

def run():
    print("📨 Analyse des tokens extraits depuis Telegram...")

    # Cherche le dernier fichier Telegram
    social_dir = "data/social"
    files = [f for f in os.listdir(social_dir) if f.startswith("telegram_messages_")]
    if not files:
        print("❌ Aucun fichier Telegram trouvé.")
        return

    latest_file = sorted(files)[-1]
    csv_path = os.path.join(social_dir, latest_file)

    # Extraction
    tokens = extract_tokens_from_csv(csv_path, top_n=10)
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
            export_results_to_csv(df, "telegram_shitcoin", config)
            print(f"✅ {symbol} : {results['total_return_%']}% | Trades : {results['nb_trades']}")

            # ✅ ENREGISTREMENT HISTORIQUE
            append_to_historique({
                "source": "Telegram",
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