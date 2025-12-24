import os
import pandas as pd
from datetime import datetime
from backtester.fetch_ohlcv import fetch_ohlcv
from backtester.momentum_strategy import backtest_momentum_strategy
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.export_results_to_csv import append_to_historique

print("🧪 Backtests sur tokens détectés depuis DEX Screener...")

csv_path = "data/social/dex_pumped_tokens.csv"
if not os.path.exists(csv_path):
    print(f"❌ Fichier non trouvé : {csv_path}")
    print("❌ Aucun token détecté.")
    exit()

df_tokens = pd.read_csv(csv_path)
tokens = df_tokens["token"].dropna().unique().tolist()

if not tokens:
    print("❌ Aucun token détecté.")
    exit()

timeframe = "1h"
start_date = "2022-01-01"
end_date = "2022-03-01"

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
            "source": "DEX",
            "strategy": "shitcoin",
            "token": real_token,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "return_pct": results["total_return_%"],
            "nb_trades": results["nb_trades"],
            "win_rate_pct": results["win_rate_%"]
        })

        print(f"⚡ Backtest MOMENTUM pour {real_token}/USDT via {exchange}")
        results_mom, df_mom = backtest_momentum_strategy(df, {
            "symbol": real_token,
            "momentum_window": 3,
            "momentum_threshold_pct": 5
        })
        print(f"✅ Momentum OK : {results_mom['total_return_%']}%")

        append_to_historique({
            "source": "DEX",
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