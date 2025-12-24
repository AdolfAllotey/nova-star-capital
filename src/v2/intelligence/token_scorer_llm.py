import os
import json
import openai
from datetime import datetime, timezone, timezone
from dotenv import load_dotenv
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_selected_tokens

# Initialisation
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
logger = get_logger("token_scorer_llm")

def get_token_score_description(token_name, context):
    try:
        prompt = f"""
        Tu es un analyste crypto. Voici le contexte pour le token "{token_name}":
        {context}

        Sur la base de ces données, donne une évaluation synthétique (en 5-10 lignes) de la qualité et du potentiel de ce token.
        Utilise un ton professionnel et factuel.
        """
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Erreur lors de la génération de description pour {token_name} : {e}")
        return None

def score_tokens_with_llm(selected_tokens, context_dir, output_path):
    results = {}
    for token in selected_tokens:
        context_path = os.path.join(context_dir, f"{token}.txt")
        if not os.path.exists(context_path):
            logger.warning(f"❌ Contexte non trouvé pour {token}")
            continue

        with open(context_path, "r", encoding="utf-8") as f:
            context = f.read()

        logger.info(f"📊 Génération d'une synthèse pour {token}")
        summary = get_token_score_description(token, context)
        if summary:
            results[token] = summary

    # Sauvegarde
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ Résumés LLM sauvegardés dans {output_path}")

if __name__ == "__main__":
    try:
        context_dir = "src/v2/data/context/"
        output_path = "src/v2/data/intelligence/token_llm_descriptions.json"
        selected_tokens = load_selected_tokens()
        score_tokens_with_llm(selected_tokens, context_dir, output_path)
    except Exception as e:
        logger.critical(f"Erreur critique dans token_scorer_llm.py : {e}")