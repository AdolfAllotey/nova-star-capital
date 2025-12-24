from dotenv import load_dotenv
import os

load_dotenv()

print("TWITTER =", os.getenv("TWITTER_BEARER_TOKEN"))
print("TELEGRAM ID =", os.getenv("TELEGRAM_API_ID"))
print("TELEGRAM HASH =", os.getenv("TELEGRAM_API_HASH"))

from dotenv import load_dotenv
import os

load_dotenv()

print("🔐 Etherscan API Key:", os.getenv("ETHERSCAN_API_KEY"))
