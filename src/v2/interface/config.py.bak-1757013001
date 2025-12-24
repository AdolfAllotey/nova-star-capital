import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change_this_secret_key")
    DEBUG = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # True en prod HTTPS
    SESSION_COOKIE_SAMESITE = "Lax"