import json
import os
import re

def get_top_scored_tokens(limit=20):
    """
    Récupère les meilleurs tokens scorés à partir du fichier de score généré par le pipeline.
    Filtrage possible selon d'autres critères si nécessaire.
    """
    score_file = "data/scores/token_scores.json"

    if not os.path.exists(score_file):
        print(f"❌ Fichier introuvable : {score_file}")
        return []

    with open(score_file, "r") as f:
        data = json.load(f)

    # Tri des tokens par score décroissant
    sorted_tokens = sorted(data, key=lambda x: x.get("score", 0), reverse=True)

    # Retourne les N premiers tokens
    return sorted_tokens[:limit]


def extract_token_symbols(text):
    """
    Extrait les symboles de tokens (ex. 'ETH', 'SOL', 'BTC') depuis un texte,
    en utilisant une regex sur les majuscules (2 à 5 caractères).
    """
    tokens = re.findall(r'\b[A-Z]{2,5}\b', text)
    return list(set(tokens))