from backtester.ema_strategy import backtest_ema_strategy
from backtester.rsi_strategy import backtest_rsi_strategy
from backtester.shitcoin_strategy import backtest_shitcoin_strategy

def run_backtest(df, config):
    """
    Lancement du backtest selon la stratégie spécifiée dans la config.
    """
    strategy = config.get("strategy", "ema").lower()

    if strategy == "ema":
        return backtest_ema_strategy(df, config)
    elif strategy == "rsi":
        return backtest_rsi_strategy(df, config)
    elif strategy == "shitcoin":
        return backtest_shitcoin_strategy(df, config)
    else:
        raise ValueError(f"❌ Stratégie inconnue : {strategy}")