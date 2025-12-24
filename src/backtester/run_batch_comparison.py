import sys
import os
import pandas as pd

# 🔧 PYTHONPATH
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# ✅ Imports internes
from backtester.backtester import fetch_ohlcv, backtest_ema_strategy
from backtester.rsi_strategy import backtest_rsi_strategy
from backtester.optimizer import optimize_ema, optimize_rsi
from app_config.config_loader import load_config

def load_best_params(strategy, config, df=None):
    """
    Charge ou génère les meilleurs paramètres d'optimisation.
    """
    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start = config["start_date"]
    end = config["end_date"]
    filename = f"{strategy}_optimization_{symbol}_{timeframe}_{start}_{end}.csv"
    path = os.path.join("optimizer_results", filename)

    if not os.path.exists(path):
        print(f"⚠️  Paramètres {strategy.upper()} manquants → optimisation en cours...")

        os.makedirs("optimizer_results", exist_ok=True)
        if df is None:
            raise ValueError("📛 df requis pour optimisation automatique")

        if strategy == "ema":
            fast_range = range(5, 20, 2)
            slow_range = range(10, 50, 5)
            result_df = optimize_ema(df.copy(), config, fast_range, slow_range)
        elif strategy == "rsi":
            rsi_range = range(5, 30)
            result_df = optimize_rsi(df.copy(), config, rsi_range)
        else:
            raise ValueError("❌ Stratégie inconnue")

        result_df.to_csv(path, index=False)
        print(f"✅ Paramètres {strategy.upper()} optimisés → {path}")

    df_csv = pd.read_csv(path)
    return df_csv.iloc[0]

def run_batch():
    print("🚀 Lancement du batch : comparaison EMA vs RSI")

    symbols = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["1h", "4h"]

    config = load_config()
    start = config["start_date"]
    end = config["end_date"]

    results = []

    for symbol in symbols:
        for timeframe in timeframes:
            print(f"\n🔍 Traitement {symbol} — {timeframe}")

            config["symbol"] = symbol
            config["timeframe"] = timeframe

            try:
                df = fetch_ohlcv(config)

                # --- EMA
                ema = load_best_params("ema", config, df)
                config["ema_fast"] = int(ema["ema_fast"])
                config["ema_slow"] = int(ema["ema_slow"])
                ema_results, _ = backtest_ema_strategy(df.copy(), config)

                # --- RSI
                rsi = load_best_params("rsi", config, df)
                config["rsi_period"] = int(rsi["rsi_period"])
                rsi_results, _ = backtest_rsi_strategy(df.copy(), config)

                # 🔁 Ajouter au tableau global
                results.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "stratégie": "EMA",
                    **ema_results,
                    "paramètres": f"fast={config['ema_fast']}, slow={config['ema_slow']}"
                })
                results.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "stratégie": "RSI",
                    **rsi_results,
                    "paramètres": f"period={config['rsi_period']}"
                })

            except Exception as e:
                print(f"❌ Erreur sur {symbol} {timeframe} : {e}")

    # 💾 Export du fichier global
    os.makedirs("reports", exist_ok=True)
    output = pd.DataFrame(results)
    path = os.path.join("reports", "global_comparison.csv")
    output.to_csv(path, index=False)
    print(f"\n📄 Rapport global enregistré dans : {path}")

if __name__ == "__main__":
    run_batch()