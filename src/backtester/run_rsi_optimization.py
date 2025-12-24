import sys
import os

# 🔧 Ajouter src/ au PYTHONPATH
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# ✅ Imports internes
from backtester.backtester import fetch_ohlcv
from backtester.optimizer import optimize_rsi
from app_config.config_loader import load_config
import matplotlib.pyplot as plt
import pandas as pd

def main():
    print("🚀 Lancement de l'optimisation RSI...")

    # 📥 Charger la config et les données OHLCV
    config = load_config()
    df = fetch_ohlcv(config)

    # 🔁 Plage des périodes RSI à tester
    rsi_range = range(5, 30)  # Ex. : 5 à 29

    # ⚙️ Lancement de l'optimisation
    results_df = optimize_rsi(df, config, rsi_range)

    print("\n🏆 Meilleurs résultats RSI :")
    print(results_df.head())

    # 💾 Export CSV
    output_dir = "optimizer_results"
    os.makedirs(output_dir, exist_ok=True)

    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start = config["start_date"]
    end = config["end_date"]
    output_file = f"rsi_optimization_{symbol}_{timeframe}_{start}_{end}.csv"
    output_path = os.path.join(output_dir, output_file)

    results_df.to_csv(output_path, index=False)
    print(f"\n💾 Résultats enregistrés dans : {output_path}")

    # 📈 Graphique : performance par période
    plt.figure(figsize=(10, 5))
    plt.plot(results_df["rsi_period"], results_df["total_return_%"], marker="o")
    plt.xlabel("RSI Period")
    plt.ylabel("Total Return (%)")
    plt.title("Optimisation RSI — Performance par période")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()