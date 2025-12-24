import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backtester import fetch_ohlcv, export_results_to_csv
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.momentum_strategy import backtest_momentum_strategy
from backtester.export_results_to_csv import append_to_historique
from app_config.config_loader import load_config
from social.reddit_scraper import scan_reddit_for_tokens, extract_reddit_tokens

from textblob import TextBlob  # pip install textblob

def run():
    print("👽 Scraping Reddit...")
    path = scan_reddit_for_tokens()

    print("🔍 Extraction de tokens...")
    tokens = extract_reddit_tokens(path)
    print(f"🔥 Tokens valides à backtester : {tokens}")

    if not tokens:
        print("❌ Aucun token détecté.")
        return

    df_posts = pd.read_csv(path)

    sentiment_summary = []

    for token in tokens:
        symbol = f"{token}/USDT"

        # Backtest Shitcoin
        config = load_config()
        config.update({"strategy": "shitcoin", "symbol": symbol})
        print(f"💣 Backtest SHITCOIN pour {symbol}")
        try:
            df = fetch_ohlcv(config)
            results, df = backtest_shitcoin_strategy(df, config)
            export_results_to_csv(df, "reddit_shitcoin", config)
            append_to_historique({
                "source": "Reddit",
                "strategy": config["strategy"],
                "token": token,
                "timeframe": config["timeframe"],
                "start_date": config["start_date"],
                "end_date": config["end_date"],
                "return_pct": results["total_return_%"],
                "nb_trades": results["nb_trades"],
                "win_rate_pct": results["win_rate_%"],
            })
            print(f"✅ Shitcoin OK : {results['total_return_%']}%")
        except Exception as e:
            print(f"⛔ Shitcoin échoué pour {symbol} : {e}")

        # Sentiment Analysis
        mentions = df_posts[df_posts["title"].str.contains(token, case=False, na=False)]
        polarities = [TextBlob(title).sentiment.polarity for title in mentions["title"]]
        avg_polarity = round(sum(polarities) / len(polarities), 4) if polarities else 0
        sentiment_summary.append({"token": token, "mentions": len(mentions), "avg_sentiment": avg_polarity})

    if sentiment_summary:
        sentiment_df = pd.DataFrame(sentiment_summary)
        os.makedirs("data/social", exist_ok=True)
        sentiment_df.to_csv("data/social/reddit_sentiment_summary.csv", index=False)
        print("✅ Sentiment exporté dans data/social/reddit_sentiment_summary.csv")

if __name__ == "__main__":
    run()
