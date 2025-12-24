import praw
import os
from dotenv import load_dotenv

load_dotenv("reddit.env")

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent="botcrypto-script"
)

print("✅ Authentifié ! Utilisateur :", reddit.user.me())
