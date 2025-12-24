import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

# 🔧 Ajouter src/ au PYTHONPATH
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# ✅ Imports internes
from backtester.backtester import fetch_ohlcv, backtest_ema_strategy
from backtester.rsi_strategy import backtest_rsi_strategy
from app_config.config_loader import load_config

def load_best_params(strategy, config):
    """
    Charge les meilleurs paramètres depuis les fichiers d'optimisation CSV.
    """
    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start = config["start_date"]
    end = config["end_date"]
    filename = f"{strategy}_optimization_{symbol}_{timeframe}_{start}_{end}.csv"
    filepath = os.path.join("optimizer_results", filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"⚠️ Fichier non trouvé : {filepath}")

    df = pd.read_csv(filepath)
    best = df.iloc[0]

    if strategy == "ema":
        return int(best["ema_fast"]), int(best["ema_slow"])
    elif strategy == "rsi":
        return int(best["rsi_period"])
    else:
        raise ValueError("Stratégie inconnue")

def main():
    print("📊 Comparaison EMA vs RSI (paramètres optimisés)")

    config = load_config()
    df = fetch_ohlcv(config)

    # 📥 Charger les meilleurs paramètres
    ema_fast, ema_slow = load_best_params("ema", config)
    rsi_period = load_best_params("rsi", config)

    # ✅ Backtest EMA
    config["ema_fast"] = ema_fast
    config["ema_slow"] = ema_slow
    ema_results, df_ema = backtest_ema_strategy(df.copy(), config)
    df_ema["cumulative_return"] = (1 + df_ema["strategy_returns"].fillna(0)).cumprod()

    # ✅ Backtest RSI
    config["rsi_period"] = rsi_period
    rsi_results, df_rsi = backtest_rsi_strategy(df.copy(), config)
    df_rsi["cumulative_return"] = (1 + df_rsi["returns"].fillna(0)).cumprod()

    # 🔍 Résumé
    print("\n🔧 Meilleurs paramètres utilisés :")
    print(f"EMA → fast = {ema_fast}, slow = {ema_slow}")
    print(f"RSI → period = {rsi_period}")

    print("\n📈 Performances :")
    print(f"EMA → {ema_results}")
    print(f"RSI → {rsi_results}")

    # 📈 Graphe comparatif
    plt.figure(figsize=(12, 6))
    plt.plot(df_ema.index, df_ema["cumulative_return"], label=f"EMA ({ema_fast}/{ema_slow})", color="blue")
    plt.plot(df_rsi.index, df_rsi["cumulative_return"], label=f"RSI ({rsi_period})", color="orange")
    plt.title("Comparaison des rendements cumulés : EMA vs RSI (optimisés)")
    plt.xlabel("Date")
    plt.ylabel("Rendement cumulé")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
        # 💾 Sauvegarde du graphique
    output_dir = os.path.join("charts", "compare")
    os.makedirs(output_dir, exist_ok=True)

    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start = config["start_date"]
    end = config["end_date"]

    filename = f"comparison_ema_vs_rsi_{symbol}_{timeframe}_{start}_{end}.png"
    output_path = os.path.join(output_dir, filename)

    plt.savefig(output_path)
    print(f"\n🖼️ Graphique sauvegardé dans : {output_path}")
    plt.show()
        # 🧾 Résumé CSV des performances
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)

        # 🧾 Résumé CSV des performances avec paramètres
    summary = pd.DataFrame([
        {
            "stratégie": "EMA",
            **ema_results,
            "paramètres": f"fast={ema_fast}, slow={ema_slow}"
        },
        {
            "stratégie": "RSI",
            **rsi_results,
            "paramètres": f"period={rsi_period}"
        }
    ])

    report_file = f"comparison_ema_vs_rsi_{symbol}_{timeframe}_{start}_{end}.csv"
    report_path = os.path.join(report_dir, report_file)

    summary.to_csv(report_path, index=False)
    print(f"\n📄 Résumé CSV enregistré dans : {report_path}")

if __name__ == "__main__":
    main()