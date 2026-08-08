import os
import openai
from dotenv import load_dotenv
from src.v2.intelligence.llm_json_parser import (
    parse_llm_json_object,
    require_string,
)
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

# Chargement des variables d’environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4"

logger = get_logger("summarize_worst_trades")

def load_worst_trades(filepath="src/v2/data/risk/worst_trades.json") -> list:
    try:
        return load_json_file(filepath)
    except Exception as e:
        logger.error(f"Erreur lors du chargement des pires trades : {e}")
        return []

def generate_summary(trades: list) -> dict:
    try:
        formatted = "\n".join([f"- {t['symbol']}: {t['pnl_eur']}€ | Reason: {t.get('reason', 'N/A')}" for t in trades])
        prompt = f"""
You are a crypto trading analyst AI.

You are given a list of the worst simulated trades of the day:

{formatted}

Please summarize key mistakes or patterns, and suggest one improvement for the trading strategy.

Return in JSON:
{{
  "summary": "...",
  "main_mistake": "...",
  "recommendation": "..."
}}
        """

        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=400
        )

        content = response.choices[0].message["content"]
        payload = parse_llm_json_object(content)

        return {
            "summary": require_string(
                payload,
                "summary",
            ),
            "main_mistake": require_string(
                payload,
                "main_mistake",
            ),
            "recommendation": require_string(
                payload,
                "recommendation",
            ),
        }

    except Exception as e:
        logger.exception("Erreur lors du résumé des pires trades")
        return {
            "summary": "Résumé non disponible.",
            "main_mistake": "unknown",
            "recommendation": "N/A"
        }

def main():
    trades = load_worst_trades()
    if not trades:
        logger.warning("Aucun trade à résumer.")
        return
    summary = generate_summary(trades)
    save_json_file(summary, "src/v2/data/intelligence/worst_trades_summary.json")
    logger.info("Résumé LLM des pires trades sauvegardé avec succès.")

if __name__ == "__main__":
    main()