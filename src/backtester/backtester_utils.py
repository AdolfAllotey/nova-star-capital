import ccxt
import pandas as pd
from datetime import datetime
import time
import os

def fetch_ohlcv(config):
    """
    Récupère les données OHLCV depuis un cache local (CSV) si disponible,
    sinon télécharge depuis Binance via l'API publique et les enregistre.
    """
    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start_date = config["start_date"]
    end_date = config["end_date"]

    filename = f"ohlcv_{symbol}_{timeframe}_{start_date}_{end_date}.csv"
    cache_path = os.path.join("data", filename)

    os.makedirs("data", exist_ok=True)

    # 📁 Chargement depuis cache local
    if os.path.exists(cache_path):
        print(f"📁 Chargement depuis le cache local : {cache_path}")
        df = pd.read_csv(cache_path, parse_dates=["timestamp"])
        return df

    print("🌐 Données non trouvées en cache, téléchargement depuis Binance...")

    exchange = ccxt.binance()
    since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

    all_ohlcv = []
    limit = 1000

    while since < end_ts:
        print(f"📦 Téléchargement depuis {datetime.fromtimestamp(since / 1000)}...")
        ohlcv = exchange.fetch_ohlcv(config["symbol"], timeframe, since, limit)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # ✅ Export CSV avec la colonne timestamp
    df.to_csv(cache_path, index=False)
    print(f"💾 Données sauvegardées dans : {cache_path}")

    return df

def backtest_ema_strategy(df, config):
    print("Exécution du backtest EMA...")

    short = config.get("ema_fast", 12)
    long = config.get("ema_slow", 26)

    df["ema_fast"] = df["close"].ewm(span=short, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=long, adjust=False).mean()

    df["signal"] = 0
    df.loc[df["ema_fast"] > df["ema_slow"], "signal"] = 1
    df.loc[df["ema_fast"] < df["ema_slow"], "signal"] = -1

    df["strategy_returns"] = df["signal"].shift(1) * df["close"].pct_change()
    df["return_pct"] = df["strategy_returns"] * 100  # 📈 Utilisé pour le graphique

    total_return = (1 + df["strategy_returns"].fillna(0)).prod() - 1
    nb_trades = int((df["signal"].diff() != 0).sum())
    win_rate = (df["strategy_returns"] > 0).sum() / (df["strategy_returns"] != 0).sum() * 100 if (df["strategy_returns"] != 0).sum() > 0 else 0

    results = {
        "total_return_%": round(total_return * 100, 2),
        "nb_trades": nb_trades,
        "win_rate_%": round(win_rate, 2)
    }

    return results, df

def export_results_to_csv(df, strategy_name, config):
    symbol = config["symbol"].replace("/", "")
    timeframe = config["timeframe"]
    start_date = config["start_date"]
    end_date = config["end_date"]

    output_dir = os.path.join("data", "results")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{strategy_name}_{symbol}_{timeframe}_{start_date}_{end_date}.csv"
    output_path = os.path.join(output_dir, filename)
    df.to_csv(output_path, index=False)
    print(f"📤 Résultats exportés dans : {output_path}")

    archive_dir = os.path.join("data", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"{strategy_name}_{symbol}_{timeframe}_{start_date}_{end_date}_{timestamp}.csv"
    archive_path = os.path.join(archive_dir, archive_filename)
    df.to_csv(archive_path, index=False)
    print(f"📦 Résultat archivé dans : {archive_path}")