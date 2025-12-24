import requests

def fetch_trending_dex_tokens(chain_filter="ethereum", top_n=10):
    url = "https://api.dexscreener.com/latest/dex/pairs"
    print("🔍 Récupération des tokens DEX en tendance...")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        pairs = data.get("pairs", [])

        if chain_filter:
            pairs = [p for p in pairs if p.get("chainId") == chain_filter]

        trending = []
        for pair in pairs[:top_n]:
            symbol = pair["baseToken"]["symbol"]
            price = pair["priceUsd"]
            volume = pair["volume"]["h24"]
            trending.append({
                "symbol": symbol,
                "price_usd": price,
                "volume_usd": volume
            })

        return trending

    except Exception as e:
        print(f"❌ Erreur DEX API : {e}")
        return []

# Test direct
if __name__ == "__main__":
    tokens = fetch_trending_dex_tokens(chain_filter="ethereum", top_n=10)
    if tokens:
        print("🔥 Tokens DEX en tendance :")
        for t in tokens:
            print(f"{t['symbol']}: ${t['price_usd']} | Volume: ${t['volume_usd']}")
    else:
        print("❌ Aucun token détecté.")