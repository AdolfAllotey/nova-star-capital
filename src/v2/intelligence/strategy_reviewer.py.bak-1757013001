import os
import openai
import csv
from dotenv import load_dotenv
from src/v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("strategy_reviewer")

openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4"

def read_backtest_results(csv_file: str) -> str:
    """
    Lit le fichier CSV de backtest et renvoie son contenu sous forme de tableau texte.
    """
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        formatted = "\n".join([", ".join(row) for row in rows])
        return formatted

    except Exception as e:
        logger.exception("Erreur lecture CSV backtest")
        return ""

def generate_strategy_review(csv_data: str) -> str:
    """
    Appelle OpenAI pour générer une analyse stratégique lisible à partir des résultats de backtest.
    """
    try:
        prompt = f"""
You are an investment strategist AI. The following is a CSV export of several backtested strategies:

{csv_data}

Analyze these results and answer:
- Which strategy has the best balance of return and win rate?
- Which strategy is too risky or too strict?
- What strategy might be optimized or simplified?
- Give 3 clear suggestions for improving the overall strategy design.

Keep it concise (max 150 words) and write in clear bullet points.
        """.strip()

        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.6
        )

        return response.choices[0].message["content"].strip()

    except Exception as e:
        logger.exception("Erreur analyse stratégie LLM")
        return "Strategy review not available at this time."

def review_backtests(csv_file: str) -> str:
    """
    Pipeline complet : lit le CSV + appelle le LLM + renvoie le texte d'analyse.
    """
    csv_data = read_backtest_results(csv_file)
    if not csv_data:
        return "Aucune donnée de backtest disponible."
    return generate_strategy_review(csv_data)