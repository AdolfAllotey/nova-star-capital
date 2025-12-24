import pandas as pd
from backtester.backtester import backtest_ema_strategy
from backtester.rsi_strategy import backtest_rsi_strategy

def optimize_ema(df, config, fast_range, slow_range):
    """
    Optimise les paramètres EMA en testant différentes combinaisons de ema_fast et ema_slow.
    """
    results = []

    for ema_fast in fast_range:
        for ema_slow in slow_range:
            if ema_fast >= ema_slow:
                continue  # Évite les cas invalides

            config["ema_fast"] = ema_fast
            config["ema_slow"] = ema_slow

            metrics, _ = backtest_ema_strategy(df.copy(), config)
            results.append({
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                **metrics
            })

    return pd.DataFrame(results).sort_values(by="total_return_%", ascending=False)


def optimize_rsi(df, config, rsi_range):
    """
    Optimise le paramètre RSI (période) pour maximiser le rendement.
    """
    results = []

    for period in rsi_range:
        config["rsi_period"] = period
        metrics, _ = backtest_rsi_strategy(df.copy(), config)
        results.append({
            "rsi_period": period,
            **metrics
        })

    return pd.DataFrame(results).sort_values(by="total_return_%", ascending=False)
