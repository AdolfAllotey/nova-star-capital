import pandas as pd

def backtest_shitcoin_strategy(df, config):
    """
    Stratégie 'Shitcoin' : détecter des pumps rapides avec volumes élevés.
    Entrée : +X% sur N bougies et volume > moyenne.
    Sortie : bougie rouge ou drawdown.
    """

    pump_threshold = config.get("pump_threshold", 0.15)  # 15% pump
    pump_window = config.get("pump_window", 3)  # 3 bougies max
    volume_ma = config.get("volume_ma", 20)
    stop_loss = config.get("stop_loss", 0.05)

    df = df.copy()
    df["pct_change"] = df["close"].pct_change(periods=pump_window)
    df["volume_ma"] = df["volume"].rolling(volume_ma).mean()

    df["signal"] = 0
    df.loc[
        (df["pct_change"] > pump_threshold) &
        (df["volume"] > df["volume_ma"]),
        "signal"
    ] = 1

    df["position"] = 0
    df["return_pct"] = 0.0  # 👈 Initialisation pour graphique
    in_trade = False
    entry_price = 0
    returns = []

    for i in range(1, len(df)):
        if df["signal"].iloc[i] == 1 and not in_trade:
            in_trade = True
            entry_price = df["close"].iloc[i]
            df.at[df.index[i], "position"] = 1

        elif in_trade:
            current_price = df["close"].iloc[i]
            change = (current_price / entry_price) - 1

            # Sortie si bougie rouge ou perte > stop
            if df["close"].iloc[i] < df["open"].iloc[i] or change <= -stop_loss:
                returns.append(change)
                in_trade = False
                df.at[df.index[i], "return_pct"] = change * 100  # ✨ Retour à la sortie
            else:
                df.at[df.index[i], "position"] = 1
                df.at[df.index[i], "return_pct"] = (df["close"].iloc[i] / df["close"].iloc[i-1] - 1) * 100

    total_return = (1 + pd.Series(returns)).prod() - 1 if returns else 0
    win_rate = 100 * sum(1 for r in returns if r > 0) / len(returns) if returns else 0

    result = {
        "total_return_%": round(total_return * 100, 2),
        "nb_trades": len(returns),
        "win_rate_%": round(win_rate, 2)
    }

    return result, df