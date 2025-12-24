from dotenv import load_dotenv
import os

load_dotenv()

print("🔎 Vérification des variables Reddit :")
print("REDDIT_CLIENT_ID =", os.getenv("REDDIT_CLIENT_ID"))
print("REDDIT_CLIENT_SECRET =", os.getenv("REDDIT_CLIENT_SECRET"))
print("REDDIT_USER_AGENT =", os.getenv("REDDIT_USER_AGENT"))