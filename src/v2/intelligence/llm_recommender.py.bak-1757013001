# src/v2/intelligence/llm_recommender.py

import os
from dotenv import load_dotenv
from src.v2.utils.file_utils import load_json_file, save_json_file, ensure_directory_exists
from src.v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("llm_recommender")

SUMMARY_PATH = "src/v2/data/risk/worst_trades_summary.json"
BLACKLIST_PATH = "src/v2/data/risk/token_blacklist.json"

def extract_blacklist_tokens(summary_text: str):
    summary_text = summary_text.lower()
    keywords = ["blacklist", "à éviter", "à exclure"]
    tokens_to_blacklist = []

    if any(word in summary_text for word in keywords):
        words = summary_text.replace(",", " ").replace(".", " ").split()
        for word in words:
            word = word.strip().lower()
            if len(word) > 2 and word.isalpha() and word not in tokens_to_blacklist:
                tokens_to_blacklist.append(word)

    return tokens_to_blacklist

def update_blacklist_from_summary():
    logger.info("🔍 Lecture du résumé LLM pour détection des tokens à blacklister...")

    try:
        summary_data = load_json_file(SUMMARY_PATH)
    except Exception as e:
        logger.warning(f"⚠️ Impossible de lire le fichier de résumé : {e}")
        return

    # Gère le cas où le fichier est une chaîne (mauvais format)
    if isinstance(summary_data, str):
        summary_text = summary_data
    elif isinstance(summary_data, dict):
        summary_text = summary_data.get("summary", "")
    else:
        logger.warning("⚠️ Format inattendu du résumé LLM.")
        return

    if not summary_text:
        logger.warning("⚠️ Aucun contenu dans le résumé LLM.")
        return

    tokens = extract_blacklist_tokens(summary_text)

    if not tokens:
        logger.info("✅ Aucun token à blacklister détecté.")
        return

    logger.info(f"🛑 Tokens à blacklister détectés : {tokens}")

    try:
        blacklist = load_json_file(BLACKLIST_PATH)
        if not isinstance(blacklist, list):
            blacklist = []
    except Exception:
        blacklist = []

    initial_len = len(blacklist)

    for token in tokens:
        if token not in blacklist:
            blacklist.append(token)

    if len(blacklist) > initial_len:
        ensure_directory_exists(BLACKLIST_PATH)
        save_json_file(BLACKLIST_PATH, blacklist)
        logger.info(f"✅ Blacklist mise à jour avec {len(blacklist) - initial_len} nouveaux tokens.")
    else:
        logger.info("📌 Aucun nouveau token ajouté à la blacklist.")

if __name__ == "__main__":
    update_blacklist_from_summary()