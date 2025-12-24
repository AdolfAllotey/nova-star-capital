import os
import datetime
from src.v2.utils.telegram_utils import send_telegram_message

def generate_social_report():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    input_path = f"src/v2/data/social/social_sentiment.json"
    output_path = f"src/v2/data/reports/social_report_{date_str}.txt"

    if not os.path.exists(input_path):
        print("❌ Fichier de sentiment introuvable.")
        return

    try:
        with open(input_path, "r") as f:
            data = f.read()

        with open(output_path, "w") as f:
            f.write("📊 Rapport de sentiment social\n")
            f.write("==============================\n")
            f.write(data)

        print(f"✅ Rapport social enregistré : {output_path}")
        send_telegram_message("📎 Rapport social du jour", file_path=output_path)

    except Exception as e:
        print(f"❌ Erreur lors de la génération du rapport social : {e}")