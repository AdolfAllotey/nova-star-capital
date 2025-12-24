import os
import sys

# Ajouter le chemin 'src' au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# ✅ Imports internes
from backtester.backtester import fetch_ohlcv
from backtester.rsi_strategy import backtest_rsi_strategy
from app_config.config_loader import load_config

def main():
    print("📈 Test de backtest RSI en cours...")

    # Charger la configuration
    config = load_config()
    config["strategy"] = "rsi"

    # Récupérer les données OHLCV
    df = fetch_ohlcv(config)

    # Lancer le backtest RSI
    results, df = backtest_rsi_strategy(df, config)

    # Afficher les résultats
    print("✅ Résultats du backtest RSI :")
    for key, value in results.items():
        print(f"{key}: {value}")

    # Afficher un aperçu des données
    print("\n📊 Aperçu des données :")
    print(df[["timestamp", "close", "rsi", "signal", "position", "return_pct"]].tail(10))

if __name__ == "__main__":
    main()