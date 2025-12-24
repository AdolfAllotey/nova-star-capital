import os
import csv
import re
import json
from datetime import datetime
from src.utils.token_utils import extract_token_symbols


def scrape_telegram_messages():
    """
    Mock pour la V1 – simule le scraping Telegram.
    Ce bloc permet au pipeline de fonctionner même sans scraping réel.
    """
    print("📥 Scraping Telegram désactivé en V1 (mock activé)")
    return


def extract_tokens_from_csv(file_path):
    """
    Extrait les tokens détectés à partir d’un fichier CSV Telegram.
    Retourne une liste unique de symboles de tokens.
    """
    tokens_detectés = set()
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                message = row.get("message", "")
                tokens = extract_token_symbols(message)
                tokens_detectés.update(tokens)
    except Exception as e:
        print(f"[Erreur] Impossible de lire le fichier {file_path} : {e}")
    return list(tokens_detectés)


def extract_telegram_messages(json_data, group_name):
    """
    Extrait les messages pertinents d’un groupe Telegram à partir des données JSON.
    """
    messages = []
    for message in json_data.get("messages", []):
        if message.get("type") == "message" and "text" in message:
            text = message["text"]
            if isinstance(text, list):
                text = "".join([t if isinstance(t, str) else t.get("text", "") for t in text])
            messages.append({
                "group": group_name,
                "date": message.get("date"),
                "message": text
            })
    return messages


def save_messages_to_csv(messages, output_path):
    """
    Sauvegarde les messages extraits dans un fichier CSV.
    """
    fieldnames = ["group", "date", "message"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for msg in messages:
            writer.writerow(msg)


if __name__ == "__main__":
    # Exemple de test local
    test_csv = "data/telegram/telegram_group_export.csv"
    tokens = extract_tokens_from_csv(test_csv)
    print("Tokens détectés :", tokens)