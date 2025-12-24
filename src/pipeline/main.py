import os
from src.social.telegram_scraper import scrape_telegram_messages
from src.social.reddit_scraper import scrape_reddit_posts
# from src.social.twitter_scraper import detect_trending_tokens  # désactivé temporairement
from src.trading.generate_trade_simulation import main as simulate_trades
# from src.social.combine_social_data import combine_social_data  # à activer si disponible

def main():
    print("🚀 Lancement du scraping global...\n")

    # === Telegram
    print("📡 Scraping des groupes Telegram...")
    scrape_telegram_messages()

    # === Reddit
    print("\n👽 Scraping Reddit...")
    try:
        scrape_reddit_posts()
    except Exception as e:
        print(f"❌ Erreur scraping Reddit : {e}")

    # === Twitter (désactivé pour la V1)
    print("\n🐦 Scraping Twitter...")
    print("🔕 Twitter désactivé temporairement (voir V2 pour réactivation)")

    # === Fusion (si dispo)
    print("\n🔀 Fusion des données sociales...")
    # combine_social_data()

    # === Simulation des trades
    print("\n💸 Simulation des trades...")
    simulate_trades()

if __name__ == "__main__":
    main()