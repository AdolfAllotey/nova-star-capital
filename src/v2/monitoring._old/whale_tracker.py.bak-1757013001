# src/v2/monitoring/whale_tracker.py

import os
import json
import datetime
import requests
from src.v2.utils.telegram_utils import send_telegram_message
from src.v2.utils.logger import get_logger

logger = get_logger("whale_tracker")

# Configurations
API_KEY = "your_key_here"  # Clé pour API Whale Alert, à remplacer si activée
MOCK_ALERTS_FILE = "src/v2/tests/mock_whale_alerts.json"
SELECTED_TOKENS_FILE = "src/v2/tests/selected_tokens.json"
OUTPUT_FOLDER = "src/v2/data/whale_alerts/"
MIN_AMOUNT_USD = 500_000
SEND_ALERT = True

SEVERITY_LEVELS = {
    "moderate": (500_000, 2_000_000),
    "high": (2_000_000, 5_000_000),
    "critical": (5_000_000, float("inf"))
}

def get_severity(amount_usd):
    for level, (low, high) in SEVERITY_LEVELS.items():
        if low <= amount_usd < high:
            return level
    return "low"

def fetch_whale_alerts_from_api():
    url = f"https://api.whale-alert.io/v1/transactions?api_key={API_KEY}&min_value={MIN_AMOUNT_USD}&currency=usd"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("transactions", [])
        else:
            logger.warning(f"Erreur API Whale Alert: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API Whale: {e}")
        return []

def load_mock_alerts():
    try:
        with open(MOCK_ALERTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Fichier mock non trouvé: {MOCK_ALERTS_FILE}")
        return []

def load_selected_tokens():
    if not os.path.exists(SELECTED_TOKENS_FILE):
        logger.warning("Fichier des tokens sélectionnés introuvable.")
        return []
    with open(SELECTED_TOKENS_FILE, "r") as f:
        return json.load(f)

def filter_alerts(alerts, selected_tokens):
    filtered = []
    for alert in alerts:
        amount_usd = alert.get("amount_usd", 0)
        symbol = alert.get("symbol", "").upper()
        if amount_usd >= MIN_AMOUNT_USD and symbol in selected_tokens:
            alert["severity"] = get_severity(amount_usd)
            filtered.append(alert)
    return filtered

def save_alerts(alerts):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    today = datetime.date.today().isoformat()
    output_path = os.path.join(OUTPUT_FOLDER, f"{today}_whale_alerts.json")
    with open(output_path, "w") as f:
        json.dump(alerts, f, indent=2)
    return output_path

def notify_via_telegram(alerts):
    for alert in alerts:
        msg = (
            f"🚨 *Whale Alert Detected*\n"
            f"Token: `{alert['symbol']}`\n"
            f"Montant: ${alert['amount_usd']:,.0f} USD\n"
            f"Type: {alert.get('transaction_type', 'N/A')}\n"
            f"Gravité: {alert['severity'].upper()}"
        )
        send_telegram_message(msg, parse_mode="Markdown")

def run_whale_tracker():
    logger.info("🔍 Démarrage du module Whale Tracker...")

    selected_tokens = load_selected_tokens()
    alerts = load_mock_alerts()  # Remplacer par fetch_whale_alerts_from_api() si API active
    filtered_alerts = filter_alerts(alerts, selected_tokens)

    if not filtered_alerts:
        logger.info("Aucune alerte whale pertinente aujourd'hui.")
        return

    save_path = save_alerts(filtered_alerts)
    logger.info(f"{len(filtered_alerts)} alertes sauvegardées dans {save_path}")

    if SEND_ALERT:
        notify_via_telegram(filtered_alerts)
        logger.info("📩 Alertes Telegram envoyées.")