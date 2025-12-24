"""
Configuration V2 pour le bot crypto
"""

# ⚙️ Paramètres généraux
TRADING_ACCOUNT_NAME = "main_trading_account"
SECURITY_ACCOUNT_NAME = "reserve_security"
TAX_ACCOUNT_NAME = "reserve_tax"

# ⏱️ Fréquence de traitement (en minutes)
SIMULATION_INTERVAL_MINUTES = 30

# 📈 Règles de répartition des gains
REPARTITION_RULES = {
    "min_total_balance_to_activate": 5000,  # € - Seuil d’activation de la répartition
    "trading_percentage": 0.70,             # 70% pour continuer à trader
    "security_percentage": 0.20,            # 20% vers une réserve (actifs plus stables)
    "tax_percentage": 0.10                  # 10% vers la réserve impôt
}

# 📊 Fiscalité SASU (à affiner si besoin dans le futur)
TAX_SYSTEM = {
    "legal_structure": "SASU",
    "taxation_type": "Impôt sur les Sociétés",
    "tax_rate": 0.15,  # 15% jusqu’à 42 500€, puis 25%
    "tax_trigger_threshold": 42500
}

# 🔒 API Binance (exemples - à sécuriser ensuite via .env ou vault)
BINANCE_API_KEY = "your_api_key"
BINANCE_API_SECRET = "your_api_secret"
