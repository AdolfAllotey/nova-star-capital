import os
import openai
import logging
from src.v2.utils.file_utils import load_json_file, save_json_file

# Configuration du logger
from src.v2.utils.logger import get_logger
logger = get_logger("llm_analyzer")

# Configuration OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_worst_trades_summary():
    logger.info("🧠 Génération du résumé LLM des pires trades...")

    try:
        trades = load_json_file("src/v2/data/risk/worst_trades.json", fallback=[])
        if not trades:
            logger.warning("⚠️ Aucun trade trouvé dans worst_trades.json")
            return

        prompt = (
            "Voici une liste de 3 mauvais trades réalisés par un bot de trading. "
            "Génère un court résumé de ces échecs, identifie les erreurs potentielles et propose des axes d’amélioration. "
            "Format : 2 à 3 phrases.\n\n"
            f"{trades}"
        )

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un analyste en trading algorithmique."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )

        summary = response.choices[0].message.content.strip()
        save_json_file("src/v2/data/reports/worst_trades_summary.json", {"summary": summary})
        logger.info("✅ Résumé LLM généré et sauvegardé avec succès.")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du résumé LLM : {e}")

if __name__ == "__main__":
    generate_worst_trades_summary()