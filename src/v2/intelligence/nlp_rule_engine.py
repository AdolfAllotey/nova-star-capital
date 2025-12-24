import os
import json
import openai
from pathlib import Path

# Clé API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Chemins des fichiers
TOKENS_FILE = Path("src/v2/data/selected_tokens.json")
OUTPUT_FILE = Path("src/v2/data/llm_token_recommendations.json")


def load_tokens():
    try:
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur de lecture des tokens : {e}")
        return []


def analyze_tokens_with_rules(tokens):
    try:
        prompt = (
            "Voici une liste de tokens sélectionnés pour investissement :\n\n"
            f"{json.dumps(tokens, indent=2)}\n\n"
            "Sur cette base, applique les règles suivantes :\n"
            "- Écarter les tokens à faible volume ou trop risqués\n"
            "- Identifier ceux avec fort potentiel à court terme\n"
            "- Donner une recommandation claire : acheter, ignorer, ou surveiller\n"
            "- Expliquer la raison de chaque recommandation\n\n"
            "Rends le tout sous forme de liste JSON contenant les champs : token, recommandation, justification."
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un analyste crypto expert en tri de tokens."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1200,
        )

        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"❌ Erreur LLM : {e}")
        return None


def save_recommendations(summary_text):
    try:
        with open(OUTPUT_FILE, "w") as f:
            f.write(summary_text)
        print(f"✅ Recommandations sauvegardées dans {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde : {e}")


def run_nlp_rule_engine():
    print("📥 Chargement des tokens sélectionnés...")
    tokens = load_tokens()
    if not tokens:
        print("❌ Aucun token chargé.")
        return

    print("🧠 Analyse via OpenAI en cours...")
    summary = analyze_tokens_with_rules(tokens)
    if not summary:
        print("❌ L’analyse a échoué.")
        return

    print("💾 Sauvegarde des recommandations...")
    save_recommendations(summary)
    print("✅ NLP rule engine terminé.")


if __name__ == "__main__":
    run_nlp_rule_engine()