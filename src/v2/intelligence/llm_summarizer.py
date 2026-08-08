import os
import json
from dotenv import load_dotenv
import openai
from datetime import datetime, timezone
from src.v2.intelligence.llm_json_parser import (
    parse_llm_json_object,
    require_string,
    require_string_list,
)
from src.v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("llm_summarizer")

# Configuration OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4"  # ou gpt-3.5-turbo si besoin

# 📥 Entrées
GLOBAL_PERF_FILE = "src/v2/data/scores/global_performance.json"
WORST_TRADES_FILE = "src/v2/data/risk/worst_trades.json"
FINAL_SCORES_FILE = "src/v2/data/scores/final_scores.json"

# 📤 Sortie
SUMMARY_FILE = "src/v2/data/intelligence/llm_summary.json"

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Erreur lecture {path} : {e}")
        return {}

def generate_llm_summary():
    logger.info("🧠 Génération du résumé LLM...")

    global_perf = load_json(GLOBAL_PERF_FILE)
    worst_trades = load_json(WORST_TRADES_FILE)
    final_scores = load_json(FINAL_SCORES_FILE)

    # 🧾 Construction du prompt
    prompt = f"""
You are a financial analysis assistant. Based on the following data, provide a concise summary of today's trading session for internal reporting.

Global performance:
{json.dumps(global_perf, indent=2)}

Worst trades:
{json.dumps(worst_trades[:3], indent=2)}

Final scores of selected tokens:
{json.dumps(final_scores[:5], indent=2)}

Respond in JSON format:
{{
  "summary": "max 3 sentences summary of performance and actions to take",
  "highlight_tokens": ["symbols of tokens to watch or avoid"]
}}
    """

    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )

        result = response.choices[0].message["content"]
        payload = parse_llm_json_object(result)

        summary_data = {
            "summary": require_string(
                payload,
                "summary",
            ),
            "highlight_tokens": require_string_list(
                payload,
                "highlight_tokens",
                max_items=20,
                max_item_length=100,
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
        with open(SUMMARY_FILE, "w") as f:
            json.dump(summary_data, f, indent=2)

        logger.info("✅ Résumé LLM généré avec succès.")
        return summary_data

    except Exception as e:
        logger.exception("❌ Erreur génération résumé LLM")
        return {
            "summary": "Résumé non disponible.",
            "highlight_tokens": [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    generate_llm_summary()