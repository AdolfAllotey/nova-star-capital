import os
import openai
from dotenv import load_dotenv
from src.v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("chat_interface")

openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4"

def ask_bot(question: str, context: str = "") -> str:
    """
    Pose une question au bot avec un contexte optionnel.
    Le contexte peut inclure les résultats récents, les performances, etc.
    """
    try:
        system_prompt = """
You are an intelligent crypto trading assistant.
You analyze simulation results, backtests, and user rules to guide strategy.
Always respond clearly and concisely (max 150 words).
Never invent data — base your answers on provided context only.
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\nQuestion: {question}"}
        ]

        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=messages,
            max_tokens=400,
            temperature=0.5
        )

        return response.choices[0].message["content"].strip()

    except Exception as e:
        logger.exception("Erreur lors de l'appel LLM dans chat_interface")
        return "❌ Le bot n’a pas pu répondre pour le moment."

# Exemple d’appel local (à commenter en prod)
if __name__ == "__main__":
    context = "Cumulative gain: 354 USDT. Win rate last 7 days: 63%. Main strategy: Score+Sentiment."
    print(ask_bot("Quelle stratégie semble la plus fiable ?"))