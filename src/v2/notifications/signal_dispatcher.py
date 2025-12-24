import os
import json
from datetime import datetime, timezone, timezone
from src.v2.utils.telegram_utils import send_telegram_message
from src.v2.utils.logger import get_logger

logger = get_logger("signal_dispatcher")

SIGNAL_DIR = "src/v2/data/signals/"
DISPATCH_LOG_FILE = "src/v2/data/signals/signal_dispatch_log.json"

def load_signals(filename):
    path = os.path.join(SIGNAL_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def load_dispatch_log():
    if os.path.exists(DISPATCH_LOG_FILE):
        with open(DISPATCH_LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_dispatch_log(log_data):
    with open(DISPATCH_LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)

def format_signal(signal, source):
    symbol = signal.get("symbol", "N/A")
    message = f"📢 *{source.upper()} ALERT*\n"
    message += f"🔹 Token: `{symbol}`\n"
    if "score" in signal:
        message += f"📊 Score: {signal['score']}\n"
    if "sentiment" in signal:
        message += f"💬 Sentiment: {signal['sentiment']}\n"
    if "summary" in signal:
        message += f"📝 {signal['summary']}\n"
    return message

def dispatch_signals():
    all_sources = {
        "kol": "kol_signals.json",
        "whale": "whale_signals.json",
        "airdrop": "airdrop_signals.json"
    }

    dispatched_log = load_dispatch_log()
    new_log = []
    dispatched_count = 0

    for source, filename in all_sources.items():
        signals = load_signals(filename)
        for signal in signals:
            signal_id = f"{source}_{signal.get('symbol', '')}"
            if signal_id in dispatched_log:
                continue  # already sent
            try:
                message = format_signal(signal, source)
                send_telegram_message(message)
                new_log.append(signal_id)
                dispatched_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du signal {signal_id}: {e}")

    full_log = list(set(dispatched_log + new_log))
    save_dispatch_log(full_log)

    logger.info(f"{dispatched_count} signaux envoyés.")

if __name__ == "__main__":
    dispatch_signals()