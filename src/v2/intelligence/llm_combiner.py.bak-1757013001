import os
import json
from src.v2.utils.logger import get_logger

logger = get_logger("llm_combiner")

COMBINED_PATH = "src/v2/data/scores/combined_scores.json"
LLM_PATH = "src/v2/data/scores/llm_scores.json"
OUTPUT_PATH = "src/v2/data/scores/final_scores.json"

def combine_scores():
    if not os.path.exists(COMBINED_PATH) or not os.path.exists(LLM_PATH):
        logger.error("❌ Fichiers requis manquants pour la fusion.")
        return

    with open(COMBINED_PATH, "r") as f:
        combined_scores = json.load(f)

    with open(LLM_PATH, "r") as f:
        llm_scores = json.load(f)

    final_scores = {}
    for symbol, base in combined_scores.items():
        llm = llm_scores.get(symbol, {})
        final = {
            **base,
            **llm
        }
        # Création d’un score composite enrichi (optionnel)
        final["global_score"] = round(
            (
                base.get("score", 0) * 0.5 +
                base.get("sentiment", 0) * 0.2 +
                llm.get("llm_behavior_score", 0) * 0.2 +
                llm.get("llm_ethics_score", 0) * 0.1
            ) / 1.0, 4
        )
        final_scores[symbol] = final

    with open(OUTPUT_PATH, "w") as f:
        json.dump(final_scores, f, indent=2)

    logger.info(f"✅ Fusion terminée. Résultat disponible dans {OUTPUT_PATH}")

if __name__ == "__main__":
    combine_scores()