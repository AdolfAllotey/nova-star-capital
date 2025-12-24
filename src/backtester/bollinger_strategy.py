import pandas as pd

def backtest_bollinger_strategy(df, config):
    period = config.get("bb_period", 20)
    std_dev = config.get("bb_std_dev", 2.0)

    df = df.copy()
    df['ma'] = df['close'].rolling(window=period).mean()
    df['std'] = df['close'].rolling(window=period).std()
    df['upper'] = df['ma'] + std_dev * df['std']
    df['lower'] = df['ma'] - std_dev * df['std']

    df['signal'] = 0
    df.loc[df['close'] < df['lower'], 'signal'] = 1  # buy
    df.loc[df['close'] > df['upper'], 'signal'] = -1  # sell
    df['position'] = df['signal'].shift(1).fillna(0)

    df['return_pct'] = df['close'].pct_change() * df['position']
    df['return_pct'].fillna(0, inplace=True)

    total_return = (1 + df['return_pct']).prod() - 1

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

    df.drop(['ma', 'std', 'upper', 'lower'], axis=1, inplace=True)

    return {
        "total_return_%": round(total_return * 100, 2),
        "nb_trades": len(trades),
        "win_rate_%": round(win_rate, 2)
    }, df