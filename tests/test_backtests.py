import pandas as pd
from datetime import datetime, timedelta
from backtester.momentum_strategy import backtest_momentum_strategy

def test_momentum_backtest_basic():
    # Génération de données fictives
    timestamps = [datetime(2022, 1, 1) + timedelta(hours=i) for i in range(50)]
    close_prices = [100 + ((i % 10) * 2 - 5) for i in range(50)]  # variation simple
    df = pd.DataFrame({"timestamp": timestamps, "close": close_prices})

    config = {
        "momentum_window": 3,
        "momentum_threshold_pct": 5.0,
    }

    results, enriched_df = backtest_momentum_strategy(df, config)

    assert "return_pct" in enriched_df.columns, "❌ La colonne 'return_pct' est manquante"
    assert results["nb_trades"] >= 0, "❌ Le nombre de trades ne peut pas être négatif"
    assert isinstance(results["total_return_%"], float), "❌ Le retour doit être un float"
    print("✅ Test de stratégie momentum réussi.")

if __name__ == "__main__":
    test_momentum_backtest_basic()