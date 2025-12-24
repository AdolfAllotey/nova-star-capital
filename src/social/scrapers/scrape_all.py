from social.scrapers.scrape_telegram_groups import scrape_telegram_groups
from social.scrapers.scrape_twitter_trending import scrape_twitter
from social.scrapers.scrape_reddit_posts import scrape_reddit

def main():
    print("\n🚀 Lancement du scraping global...\n")

    print("\n📡 Scraping des groupes Telegram...")
    scrape_telegram_groups()

    print("\n🐦 Scraping de Twitter...")
    scrape_twitter()

    print("\n👽 Scraping de Reddit...")
    scrape_reddit()

if __name__ == "__main__":
    main()
