import os
import json
from dotenv import load_dotenv
import openai

from src.v2.intelligence.llm_json_parser import (
    parse_llm_json_object,
    require_string,
    require_string_list,
)
from src.v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("llm_summary")
openai.api_key = os.getenv("OPENAI_API_KEY")

TRADES_FILE = "src/v2/data/simulation/trades_simulated.json"
SUMMARY_FILE = "src/v2/data/intelligence/trade_summary_llm.json"
MODEL = "gpt-4"  # ou "gpt-3.5-turbo"

def load_trades():
    if not os.path.exists(TRADES_FILE):
        logger.warning(f"{TRADES_FILE} introuvable.")
        return []
    with open(TRADES_FILE, "r") as f:
        return json.load(f)


def generate_prompt(trades: list) -> str:
    lines = []
    for t in trades:
        lines.append(f"- {t.get('symbol')}: {t.get('gain_percent', 0)}% gain")
    body = "\n".join(lines)

    prompt = f"""
You are a crypto portfolio assistant.

Based on the following simulated trades, generate a short and professional performance summary (max 3 bullet points + 1 conclusion):

{body}

Only return the summary in JSON format like this:
{{
  "points": [
    "Token A performed well due to...",
    "Token B underperformed...",
    "General market sentiment was..."
  ],
  "conclusion": "Today was a strong performance driven by X and Y."
}}
    """
    return prompt


def generate_summary(trades: list) -> dict:
    try:
        prompt = generate_prompt(trades)
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.5
        )
        content = response.choices[0].message["content"]
        payload = parse_llm_json_object(content)

        return {
            "points": require_string_list(
                payload,
                "points",
                max_items=3,
            ),
            "conclusion": require_string(
                payload,
                "conclusion",
            ),
        }
    except Exception as e:
        logger.exception("Erreur génération du résumé LLM")
        return {
            "points": ["Résumé non disponible."],
            "conclusion": "Aucune analyse générée."
        }


def save_summary(summary: dict):
    os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    trades = load_trades()
    if trades:
        summary = generate_summary(trades)
        save_summary(summary)
        logger.info("Résumé LLM généré et enregistré.")