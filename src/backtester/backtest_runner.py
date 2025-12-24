import sys
import os
# Ajouter le chemin racine au sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 🔧 Ajouter src/ au PYTHONPATH
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# ✅ Imports internes
from backtester.backtester import fetch_ohlcv, backtest_ema_strategy, export_results_to_csv
from backtester.rsi_strategy import backtest_rsi_strategy
from backtester.shitcoin_strategy import backtest_shitcoin_strategy
from backtester.plotting import plot_backtest
from app_config.config_loader import load_config
from utils.logger import log_backtest

# Debug (optionnel)
print("🧪 sys.path =", sys.path)

def main():
    print("Début du backtest...")

    # Charger configuration
    config = load_config()

    # Récupérer les données
    ohlcv = fetch_ohlcv(config)

    strategy = config.get("strategy", "ema").lower()

    # Lancer la bonne stratégie
    if strategy == "ema":
        print("📈 Stratégie sélectionnée : EMA")
        results, df = backtest_ema_strategy(ohlcv.copy(), config)

    elif strategy == "rsi":
        print("📉 Stratégie sélectionnée : RSI")
        results, df = backtest_rsi_strategy(ohlcv.copy(), config)

    elif strategy == "shitcoin":
        print("🚀 Stratégie sélectionnée : Shitcoin")
        results, df = backtest_shitcoin_strategy(ohlcv.copy(), config)

    else:
        raise ValueError(f"❌ Stratégie inconnue : {strategy}")

    # Export résultats CSV + archive
    export_results_to_csv(df, strategy, config)

    # Log journal
    log_backtest(results, strategy, config)

    # Afficher les résultats
    print("Résultats du backtest :")
    print(results)

    # Affichage graphique si activé
    if config.get("plot", True):
        plot_backtest(df, strategy)

if __name__ == "__main__":
    main()