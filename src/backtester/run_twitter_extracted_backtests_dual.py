import os
import pandas as pd
from datetime import datetime
from backtester.fetch_ohlcv import fetch_ohlcv
from backtester.momentum_strategy import backtest_momentum_strategy
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.export_results_to_csv import append_to_historique
from social.twitter_scraper import detect_trending_tokens

print("🧪 Backtests sur tokens détectés depuis Twitter...")

# === Paramètres généraux
timeframe = "1h"
start_date = "2022-01-01"
end_date = "2022-03-01"

tokens_raw = detect_trending_tokens()
tokens = [t[0] for t in tokens_raw]

if not tokens:
    print("❌ Aucun token détecté.")
    exit()

for token in tokens:
    is_kucoin = token.endswith("_KU")
    real_token = token.replace("_KU", "")
    exchange = "kucoin" if is_kucoin else "binance"
    print(f"\n💣 Backtest SHITCOIN pour {real_token}/USDT via {exchange}")

    try:
        df = fetch_ohlcv({
            "symbol": f"{real_token}/USDT",
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "exchange": exchange
        })
        results, df_bt = backtest_shitcoin_strategy(df, {"symbol": real_token})
        print(f"✅ Shitcoin OK : {results['total_return_%']}%")

        append_to_historique({
            "source": "Twitter",
            "strategy": "shitcoin",
            "token": real_token,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "return_pct": results["total_return_%"],
            "nb_trades": results["nb_trades"],
            "win_rate_pct": results["win_rate_%"]
        })

        # === Backtest momentum
        print(f"⚡ Backtest MOMENTUM pour {real_token}/USDT via {exchange}")
        results_mom, df_mom = backtest_momentum_strategy(df, {
            "symbol": real_token,
            "momentum_window": 3,
            "momentum_threshold_pct": 5
        })
        print(f"✅ Momentum OK : {results_mom['total_return_%']}%")

        append_to_historique({
            "source": "Twitter",
            "strategy": "momentum",
            "token": real_token,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "return_pct": results_mom["total_return_%"],
            "nb_trades": results_mom["nb_trades"],
            "win_rate_pct": results_mom["win_rate_%"]
        })

    except Exception as e:
        print(f"❌ Erreur pour {real_token} : {e}")