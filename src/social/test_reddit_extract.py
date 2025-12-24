from social.reddit_scraper import scan_reddit_for_tokens, extract_reddit_tokens

def test_reddit_extraction():
    print("🔎 Scraping Reddit...")
    csv_path = scan_reddit_for_tokens()
    print("✅ Posts Reddit récupérés.")

    print("\n🧠 Extraction des tokens Reddit...")
    tokens = extract_reddit_tokens(csv_path)
    print("🔥 Tokens les plus mentionnés :", tokens)

if __name__ == "__main__":
    test_reddit_extraction()