import sys
import os
import pandas as pd

# 🔧 PYTHONPATH
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# ✅ Imports
from backtester.backtester import fetch_ohlcv
from backtester.optimizer import optimize_ema, optimize_rsi
from app_config.config_loader import load_config

def run_batch_optimization():
    print("🚀 Lancement de l'optimisation batch EMA + RSI")

    symbols = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["1h", "4h"]

    config = load_config()
    start = config["start_date"]
    end = config["end_date"]

    for symbol in symbols:
        for timeframe in timeframes:
            print(f"\n🔍 Optimisation pour {symbol} — {timeframe}")

            config["symbol"] = symbol
            config["timeframe"] = timeframe

            try:
                df = fetch_ohlcv(config)

                # --- EMA
                fast_range = range(5, 20, 2)
                slow_range = range(10, 50, 5)
                ema_df = optimize_ema(df.copy(), config, fast_range, slow_range)

                ema_file = f"ema_optimization_{symbol.replace('/', '')}_{timeframe}_{start}_{end}.csv"
                ema_path = os.path.join("optimizer_results", ema_file)
                os.makedirs("optimizer_results", exist_ok=True)
                ema_df.to_csv(ema_path, index=False)
                print(f"✅ EMA optimisée → {ema_path}")

                # --- RSI
                rsi_range = range(5, 30)
                rsi_df = optimize_rsi(df.copy(), config, rsi_range)

                rsi_file = f"rsi_optimization_{symbol.replace('/', '')}_{timeframe}_{start}_{end}.csv"
                rsi_path = os.path.join("optimizer_results", rsi_file)
                rsi_df.to_csv(rsi_path, index=False)
                print(f"✅ RSI optimisée → {rsi_path}")

            except Exception as e:
                print(f"❌ Erreur pour {symbol} {timeframe} : {e}")

if __name__ == "__main__":
    run_batch_optimization()