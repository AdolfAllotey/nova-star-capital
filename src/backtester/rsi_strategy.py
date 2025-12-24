import pandas as pd

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_rsi_signals(df, period=14, overbought=70, oversold=30):
    """
    Ajoute les signaux RSI à un DataFrame OHLCV pour simulation.
    """
    df = df.copy()
    df['rsi'] = calculate_rsi(df, period)
    df['signal'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = 1
    df.loc[df['rsi'] > overbought, 'signal'] = -1
    return df

def backtest_rsi_strategy(df, config):
    """
    Backtest complet basé sur la stratégie RSI.
    """
    period = config.get("rsi_period", 14)
    overbought = config.get("rsi_overbought", 70)
    oversold = config.get("rsi_oversold", 30)

    df = compute_rsi_signals(df, period, overbought, oversold)

    df['position'] = df['signal'].shift(1).fillna(0)
    df['return_pct'] = df['close'].pct_change() * df['position']
    df['return_pct'] = df['return_pct'].fillna(0)

    total_return = (1 + df['return_pct'] / 100).prod() - 1

    trades = []
    current_position = 0
    entry_price = None

    for i in range(len(df)):
        signal = df['signal'].iloc[i]
        price = df['close'].iloc[i]

        if signal != current_position:
            if current_position != 0 and entry_price is not None:
                change = (price / entry_price - 1) if current_position == 1 else (entry_price / price - 1)
                trades.append(change)
            entry_price = price
            current_position = signal

    win_rate = 100 * sum(1 for t in trades if t > 0) / len(trades) if trades else 0

    return {
        "total_return_%": round(total_return * 100, 2),
        "nb_trades": len(trades),
        "win_rate_%": round(win_rate, 2)
    }, df