import pandas as pd

def compute_macd_signals(df, fast_period=12, slow_period=26, signal_period=9):
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=fast_period, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=slow_period, adjust=False).mean()
    df["macd"] = df["ema_fast"] - df["ema_slow"]
    df["macd_signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()
    return df

def backtest_macd_strategy(df, config):
    fast_period = config.get("macd_fast", 12)
    slow_period = config.get("macd_slow", 26)
    signal_period = config.get("macd_signal", 9)

    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=fast_period, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=slow_period, adjust=False).mean()
    df["macd"] = df["ema_fast"] - df["ema_slow"]
    df["macd_signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()

    df["signal"] = 0
    df.loc[(df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1)), "signal"] = 1
    df.loc[(df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1)), "signal"] = -1
    df["position"] = df["signal"].shift(1).fillna(0)

    df["return_pct"] = df["close"].pct_change() * df["position"]
    df["return_pct"].fillna(0, inplace=True)

    total_return = (1 + df["return_pct"]).prod() - 1

    trades = []
    entry_price = None
    position = 0

    for i, row in df.iterrows():
        if row["signal"] == 1:
            entry_price = row["close"]
            position = 1
        elif row["signal"] == -1 and position == 1 and entry_price is not None:
            pnl = (row["close"] - entry_price) / entry_price
            trades.append(pnl)
            position = 0
            entry_price = None

    win_rate = 100 * sum(1 for t in trades if t > 0) / len(trades) if trades else 0

    return {
        "total_return_%": round(total_return * 100, 2),
        "nb_trades": len(trades),
        "win_rate_%": round(win_rate, 2)
    }, df