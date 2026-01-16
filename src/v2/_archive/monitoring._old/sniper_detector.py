import os
import json
from datetime import datetime, timezone, timezone
from utils.telegram_bot import send_telegram_message  # Import corrigé

DATA_FOLDER = "data/v2/sniper"
os.makedirs(DATA_FOLDER, exist_ok=True)

def fetch_sniper_signals():
    """
    Exemple de récupération des signaux sniper depuis une source ou fichier local.
    """
    try:
        with open("data/samples/sniper_signals_sample.json") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Fichier de signaux Sniper non trouvé.")
        return []

def detect_snipers():
    today = datetime.now().strftime("%Y-%m-%d")
    signals = fetch_sniper_signals()

    # Filtrage simple : par exemple volume > seuil
    detected_snipers = [s for s in signals if s.get("volume", 0) > 1000]

    # Sauvegarde
    out_path = os.path.join(DATA_FOLDER, f"snipers_{today}.json")
    with open(out_path, "w") as f:
        json.dump(detected_snipers, f, indent=2)

    # Envoi Telegram
    if detected_snipers:
        message = f"🚨 **Sniper Detector - {today}**\n"
        message += f"{len(detected_snipers)} snipers détectés :\n"
        for sniper in detected_snipers[:10]:
            message += f"• {sniper['token']} - Volume : {sniper['volume']}\n"
        send_telegram_message(message)
    else:
        send_telegram_message(f"🚨 Sniper Detector - {today} : aucun sniper détecté.")

if __name__ == "__main__":
    detect_snipers()