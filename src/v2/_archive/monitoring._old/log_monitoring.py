import os
from datetime import datetime, timezone, timezone
from utils.telegram_bot import send_telegram_message  # Correction import

LOG_FOLDER = "logs"
LOG_FILE = os.path.join(LOG_FOLDER, "app.log")

def monitor_logs():
    if not os.path.exists(LOG_FILE):
        print(f"❌ Fichier de logs introuvable : {LOG_FILE}")
        return

    with open(LOG_FILE, "r") as f:
        lines = f.readlines()

    # Exemple simple : détecter erreurs récentes dans les logs
    error_lines = [line for line in lines if "ERROR" in line or "Exception" in line]

    if error_lines:
        message = f"⚠️ Logs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += "Erreurs détectées :\n"
        message += "\n".join(error_lines[-10:])  # 10 dernières erreurs
        send_telegram_message(message)
    else:
        print("✅ Aucun problème détecté dans les logs.")

if __name__ == "__main__":
    monitor_logs()