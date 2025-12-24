import os
import json
from dotenv import load_dotenv
from src.v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("worst_trades_summary")

try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    LLM_ENABLED = bool(openai.api_key)
except Exception:
    LLM_ENABLED = False

WORST_TRADES_PATH = "src/v2/data/risk/worst_trades.json"
SUMMARY_OUTPUT_PATH = "src/v2/data/risk/worst_trades_summary.json"

def summarize_worst_trades():
    if not os.path.exists(WORST_TRADES_PATH):
        logger.warning("Aucun fichier worst_trades.json trouvé.")
        return

    with open(WORST_TRADES_PATH, "r") as f:
        worst_trades = json.load(f)

    if not worst_trades:
        logger.warning("Fichier worst_trades.json vide.")
        return

    prompt = f"""
Tu es un analyste crypto. Fais un résumé en 5 lignes maximum expliquant pourquoi ces 5 tokens ont généré les pires pertes.
Voici les données :
{json.dumps(worst_trades, indent=2)}
Réponds en français dans un paragraphe concis.
"""

    summary = "L'analyse des pires trades sera disponible une fois l'API OpenAI activée."

    if LLM_ENABLED:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5,
            )
            summary = response.choices[0].message["content"]
        except Exception as e:
            logger.exception("Erreur lors du résumé LLM des pires trades.")

    with open(SUMMARY_OUTPUT_PATH, "w") as f:
        json.dump({"summary": summary}, f, indent=2)

    logger.info(f"Résumé LLM enregistré dans {SUMMARY_OUTPUT_PATH}")

if __name__ == "__main__":
    summarize_worst_trades()