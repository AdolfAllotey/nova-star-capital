import json
import os
from src.v2.utils.telegram_bot import send_telegram_message

SIGNALS_FILE = "src/v2/data/signals/filtered_signals.json"
PREFERENCES_FILE = "src/v2/data/users/telegram_preferences.json"

def load_signals():
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, "r") as f:
            return json.load(f)
    return []

def load_preferences():
    if os.path.exists(PREFERENCES_FILE):
        with open(PREFERENCES_FILE, "r") as f:
            return json.load(f)
    return {}

def dispatch_signals():
    signals = load_signals()
    prefs = load_preferences()

    for user_id, user_prefs in prefs.items():
        matched_signals = []

        for signal in signals:
            if signal["type"] in user_prefs.get("alerts", []):
                matched_signals.append(signal)

        if matched_signals:
            message = f"📢 *Nova Star Capital - Signaux sélectionnés ({len(matched_signals)})*"
            for sig in matched_signals:
                message += f"\n\n🪙 *{sig['token']}*\nType : {sig['type']}\nScore : {sig.get('score', 'N/A')}\nSentiment : {sig.get('sentiment', 'N/A')}"
            send_telegram_message(message, chat_id=user_id)

if __name__ == "__main__":
    dispatch_signals()