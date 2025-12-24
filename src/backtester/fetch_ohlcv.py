import os
import pandas as pd
import ccxt
from datetime import datetime
from time import sleep

def fetch_ohlcv(config):
    symbol = config["symbol"]
    timeframe = config.get("timeframe", "1h")
    start_date = config["start_date"]
    end_date = config["end_date"]

    # Détermine l'exchange à utiliser
    if "_KU" in symbol:
        exchange = ccxt.kucoin()
        symbol_name = symbol.replace("_KU", "")
        ccxt_symbol = f"{symbol_name}/USDT"
        exchange_name = "kucoin"
    else:
        exchange = ccxt.binance({
            'options': {
                'defaultType': 'spot'  # ⚠️ Utiliser l'API SPOT
            }
        })
        symbol_name = symbol.replace("/", "")
        ccxt_symbol = symbol
        exchange_name = "binance"

    # Fichier de cache
    cache_dir = "data/ohlcv"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"ohlcv_{symbol_name}_{timeframe}_{start_date}_{end_date}.csv")

    # Retourne les données du cache si disponibles
    if os.path.exists(cache_file):
        print(f"📁 Chargement depuis le cache local : {cache_file}")
        return pd.read_csv(cache_file, parse_dates=["timestamp"])

    print(f"⏳ Téléchargement OHLCV pour {ccxt_symbol} de {start_date} à {end_date} via {exchange_name}")

    since = exchange.parse8601(f"{start_date}T00:00:00Z")
    end_ts = exchange.parse8601(f"{end_date}T00:00:00Z")
    all_data = []
    limit = 1000

    while since < end_ts:
        try:
            ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, since=since, limit=limit)
            if not ohlcv:
                break
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df[df["timestamp"] < pd.to_datetime(end_date)]
            all_data.append(df)
            since = int(df["timestamp"].iloc[-1].timestamp() * 1000) + 1
            sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"❌ Erreur téléchargement ({exchange_name}) : {e}")
            break

    if not all_data:
        raise ValueError(f"Aucune donnée OHLCV trouvée pour {symbol} entre {start_date} et {end_date}")

    final_df = pd.concat(all_data).drop_duplicates(subset="timestamp")
    final_df.to_csv(cache_file, index=False)
    print(f"✅ Données sauvegardées dans {cache_file}")
    return final_df