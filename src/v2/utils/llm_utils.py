import openai
import os
from src.v2.utils.logger import get_logger

logger = get_logger("llm_utils")

# NSC: hard-disable LLM calls in PREPROD when NSC_LLM_ENABLED=0
import os
if os.getenv('NSC_LLM_ENABLED','1').strip().lower() in ('0','false','no','n','off'):
    raise RuntimeError('LLM disabled (NSC_LLM_ENABLED=0)')
# Clé API OpenAI (doit être définie dans ton fichier .env ou dans l'environnement)
openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_sentiment_with_openai(text):
    try:
        prompt = f"""Tu es un assistant spécialisé dans l'analyse du sentiment des messages liés à la cryptomonnaie.
Classe le sentiment général du message ci-dessous parmi les catégories suivantes : 
- haussier (bullish)
- neutre
- baissier (bearish)

Message :
{text}

Réponds uniquement par l’un des mots suivants : bullish, neutral, bearish."""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un expert en sentiment crypto."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=10
        )
        sentiment = response.choices[0].message["content"].strip().lower()
        if sentiment not in ["bullish", "neutral", "bearish"]:
            logger.warning(f"Réponse inattendue de l'API OpenAI : {sentiment}")
            return "neutral"
        return sentiment
    except Exception as e:
        logger.error(f"Erreur dans analyze_sentiment_with_openai : {e}")
        return "neutral"

def generate_summary_from_text(text, max_tokens=300):
    try:
        prompt = f"""Voici un ensemble de messages, extraits ou commentaires concernant des investissements crypto. Ton objectif est d'en faire un **résumé synthétique**, clair et structuré, en français. Le résumé doit mettre en avant les tendances clés, les points d’attention, et tout élément pertinent pour une prise de décision.

Texte à résumer :
{text}

Résumé :"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un assistant financier spécialisé dans l’analyse de contenu crypto."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=max_tokens
        )
        summary = response.choices[0].message["content"].strip()
        return summary
    except Exception as e:
        logger.error(f"Erreur dans generate_summary_from_text : {e}")
        return "Résumé indisponible."