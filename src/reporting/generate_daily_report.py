import os
from datetime import datetime
from utils.telegram_utils import send_telegram_message

def main():
    print("📤 Génération du rapport de simulation quotidien...")

    # 📁 Chemins des fichiers
    today = datetime.now().strftime("%Y%m%d")
    base_dir = "data/trades"
    txt_path = os.path.join(base_dir, "trades_simulated_latest.txt")
    report_path = os.path.join(base_dir, "trades_daily_report.txt")

    # 📄 Vérification des fichiers
    if not os.path.exists(txt_path):
        print(f"❌ Fichier texte pour Telegram introuvable : {txt_path}")
        return
    if not os.path.exists(report_path):
        print(f"❌ Rapport journalier introuvable : {report_path}")
        return

    # 📤 Lecture du message Telegram
    with open(txt_path, "r") as f:
        message = f.read()

    # 📊 Affichage du résumé console
    print(f"\n📄 Contenu du rapport à envoyer :\n{'-' * 40}")
    print(message)
    print(f"{'-' * 40}\n")

    # ✉️ Envoi Telegram
    try:
        send_telegram_message(message)
        print("✅ Rapport Telegram envoyé.")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi Telegram : {e}")

if __name__ == "__main__":
    main()