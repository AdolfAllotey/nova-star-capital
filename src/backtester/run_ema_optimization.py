import sys
import os

# 🔧 Ajouter le dossier 'src' au PYTHONPATH
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# ✅ Imports internes
from backtester.backtester import fetch_ohlcv
from backtester.optimizer import optimize_ema
from app_config.config_loader import load_config
import matplotlib.pyplot as plt
import pandas as pd

def main():
    print("🚀 Lancement de l'optimisation EMA...")

    config = load_config()
    df = fetch_ohlcv(config)

    # 💡 Plages de paramètres EMA à tester
    fast_range = range(5, 20, 2)     # 5, 7, 9, ..., 19
    slow_range = range(10, 50, 5)    # 10, 15, ..., 45

    results_df = optimize_ema(df, config, fast_range, slow_range)

    print("\n🏆 Meilleurs résultats EMA :")
    print(results_df.head())

    # 📤 Sauvegarde des résultats
    output_dir = "optimizer_results"
    os.makedirs(output_dir, exist_ok=True)

    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start = config["start_date"]
    end = config["end_date"]
    output_file = f"ema_optimization_{symbol}_{timeframe}_{start}_{end}.csv"
    output_path = os.path.join(output_dir, output_file)

    results_df.to_csv(output_path, index=False)
    print(f"\n💾 Résultats enregistrés dans : {output_path}")

    # 🔍 Affichage graphique des rendements
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(results_df["ema_fast"], results_df["ema_slow"],
                          c=results_df["total_return_%"], cmap="viridis", s=100)
    plt.colorbar(scatter, label="Total Return (%)")
    plt.xlabel("EMA Fast")
    plt.ylabel("EMA Slow")
    plt.title("Optimisation EMA — Rendement par combinaison")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()