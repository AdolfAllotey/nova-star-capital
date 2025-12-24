from social.dex_scraper import fetch_trending_dex_tokens

print("🔍 Test du scraper DEX avec le mot-clé 'pepe'...")
tokens = fetch_trending_dex_tokens("pepe")

if tokens:
    print("\n🔥 Tokens DEX détectés :")
    for token in tokens:
        print(f"- {token['symbol']}: Δ {token['price_change_%']}% | Vol ${token['volume_usd']} | Liq ${token['liquidity_usd']}")
        print(f"  🔗 {token['url']}")
else:
    print("❌ Aucun token détecté.")