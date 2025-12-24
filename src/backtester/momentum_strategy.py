import pandas as pd

def compute_momentum(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calcule le momentum simple basé sur la variation entre la dernière close et la moyenne glissante.
    """
    return (df["close"] - df["close"].rolling(window=window).mean()) / df["close"].rolling(window=window).mean() * 100

def compute_momentum_signals(df: pd.DataFrame, config: dict = None):
    """
    Ajoute les colonnes nécessaires pour l’utilisation du momentum dans les simulations.
    """
    if config is None:
        config = {"momentum_window": 3, "momentum_threshold_pct": 10}

    window = config.get("momentum_window", 3)
    threshold_pct = config.get("momentum_threshold_pct", 10)

    df = df.copy()
    df["momentum"] = compute_momentum(df, window)
    df["signal"] = "hold"
    df.loc[df["momentum"] > threshold_pct, "signal"] = "buy"
    df.loc[df["momentum"] < -threshold_pct, "signal"] = "sell"

    return df

def backtest_momentum_strategy(df: pd.DataFrame, config: dict):
    """
    Backtest d'une stratégie simple basée sur le momentum : 
    entrée si le momentum dépasse un seuil, sortie sinon.
    """
    window = config.get("momentum_window", 3)
    threshold_pct = config.get("momentum_threshold_pct", 10)

    df = df.copy()
    df["momentum"] = compute_momentum(df, window)
    df["signal"] = df["momentum"] > threshold_pct
    df["position"] = df["signal"].shift(1).fillna(False).astype(bool)

    # Calcul des performances
    df["return_pct"] = 0.0
    df.loc[df["position"], "return_pct"] = df["close"].pct_change().shift(-1) * 100

    trades = df[df["position"]]
    nb_trades = len(trades)
    win_rate = 100 * len(trades[trades["return_pct"] > 0]) / nb_trades if nb_trades > 0 else 0
    total_return = trades["return_pct"].sum() if nb_trades > 0 else 0

    results = {
        "total_return_%": round(total_return, 2),
        "nb_trades": nb_trades,
        "win_rate_%": round(win_rate, 2)
    }

    return results, df