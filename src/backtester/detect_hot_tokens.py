import ccxt
import time

def detect_hot_usdt_pairs(pump_threshold=0.15, min_volume_usdt=100000):
    """
    Scanne toutes les paires USDT et détecte celles en pump (> +15% sur 1h).
    """
    exchange = ccxt.binance()
    tickers = exchange.fetch_tickers()
    hot_pairs = []

    for symbol, data in tickers.items():
        if "/USDT" not in symbol:
            continue

        try:
            change_1h = data.get("percentage") or 0
            volume_usdt = data["quoteVolume"]

            if change_1h and change_1h > pump_threshold * 100 and volume_usdt > min_volume_usdt:
                hot_pairs.append({
                    "symbol": symbol,
                    "change_1h": round(change_1h, 2),
                    "volume_usdt": round(volume_usdt, 0)
                })

        except Exception:
            continue

    return sorted(hot_pairs, key=lambda x: -x["change_1h"])


if __name__ == "__main__":
    print("🔍 Recherche de shitcoins en pump...")
    pairs = detect_hot_usdt_pairs()
    for p in pairs:
        print(f"{p['symbol']} 📈 +{p['change_1h']}% | Volume ≈ ${p['volume_usdt']:,}")