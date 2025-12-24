import ssl
import snscrape.modules.twitter as sntwitter
import certifi
import urllib3

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings()

query = "crypto OR altcoin OR pepe OR shiba OR shitcoin OR binance"
print(f"🔍 Recherche Twitter (sans SSL vérification) : '{query}'")

for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
    print(f"{i+1}. {tweet.date} - {tweet.content[:80]}")
    if i >= 4:
        break