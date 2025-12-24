import pandas as pd

def compute_ema_signals(df, short=12, long=26):
    """
    Ajoute les colonnes ema_short, ema_long au DataFrame et retourne les signaux de croisement.
    """
    df = df.copy()
    df['ema_short'] = df['close'].ewm(span=short, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long, adjust=False).mean()
    return df

def backtest_ema_strategy(df, config):
    # Vérifie que les colonnes nécessaires sont présentes
    if 'time' in df.columns and 'timestamp' not in df.columns:
        df.rename(columns={"time": "timestamp"}, inplace=True)

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Paramètres EMA
    short = config.get("ema_short", 12)
    long = config.get("ema_long", 26)

    # Calcul des EMA et signaux
    df = compute_ema_signals(df, short, long)

    # Génération des signaux
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1
    df['position'] = df['signal'].shift()

    # Calcul des rendements
    df['return_pct'] = df['close'].pct_change() * df['position']
    df['return_pct'].fillna(0, inplace=True)

    # Statistiques
    total_return = (1 + df['return_pct']).prod() - 1
    nb_trades = df['position'].diff().abs().sum()
    win_rate = (df['return_pct'] > 0).sum() / (df['return_pct'] != 0).sum() * 100 if (df['return_pct'] != 0).sum() > 0 else 0

    results = {
        "total_return_%": round(total_return * 100, 2),
        "nb_trades": int(nb_trades),
        "win_rate_%": round(win_rate, 2)
    }

    return results, df