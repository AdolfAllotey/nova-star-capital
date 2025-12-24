import requests

def fetch_hot_dex_tokens(limit=10):
    """
    Récupère les tokens en tendance sur DexScreener en se basant sur le volume.
    """
    url = "url = "https://api.dexscreener.com/latest/dex/pairs/ethereum""
    try:
        response = requests.get(url)
        data = response.json()

        pairs = data.get("pairs", [])[:limit]
        tokens = []
        for pair in pairs:
            tokens.append({
                "symbol": pair.get("baseToken", {}).get("symbol", "N/A"),
                "volume_usd": float(pair.get("volume", {}).get("h24", 0)),
                "change_pct": float(pair.get("priceChange", {}).get("h1", 0)),
                "url": pair.get("url", "#")
            })

        return tokens
    except Exception as e:
        print(f"❌ Erreur DEX API : {e}")
        return []
