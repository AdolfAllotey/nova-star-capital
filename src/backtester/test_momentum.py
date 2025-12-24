import pandas as pd
from datetime import datetime, timedelta
from backtester.momentum_strategy import backtest_momentum_strategy

# === Génération de données fictives ===
timestamps = [datetime(2022, 1, 1) + timedelta(hours=i) for i in range(30)]
# Simule des variations modérées pour déclencher des signaux
prices = [100 + (i % 5) * 2 + (i // 5) * 3 for i in range(30)]

df = pd.DataFrame({
    "timestamp": timestamps,
    "close": prices
})

# === Configuration du backtest ===
config = {
    "momentum_window": 3,
    "momentum_threshold_pct": 2  # seuil abaissé pour déclencher des signaux
}

# === Lancement du backtest ===
results, enriched_df = backtest_momentum_strategy(df.copy(), config)

# === Affichage des résultats ===
print("\nRésultats du backtest :")
print(results)

print("\nAperçu du DataFrame enrichi :")
print(enriched_df.tail(10))  # affiche les 10 dernières lignes