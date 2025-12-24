# src/v2/scoring/ethic_scoring.py

import os
import json

ETHIC_SCORE_LOG = "data/v2/logs/ethic_scores.json"
os.makedirs(os.path.dirname(ETHIC_SCORE_LOG), exist_ok=True)

def compute_ethic_score(token_data):
    """
    Calcule un score éthique pour un token en fonction de critères de transparence, décentralisation et durabilité.

    Args:
        token_data (dict): Données du token, incluant les critères nécessaires.
    
    Returns:
        float: Score éthique (0 à 1).
    """
    score = 0
    criteria = 0

    # ✅ Décentralisation : aucun wallet ne détient > 5%
    if "max_wallet_percent" in token_data:
        criteria += 1
        if token_data["max_wallet_percent"] <= 5:
            score += 1

    # ✅ Allocation team/VC < 25%
    if "team_allocation_percent" in token_data:
        criteria += 1
        if token_data["team_allocation_percent"] <= 25:
            score += 1

    # ✅ Activité GitHub
    if "github_activity" in token_data:
        criteria += 1
        if token_data["github_activity"]:  # True si actif
            score += 1

    # ✅ Présence de mécanismes de burn ou tax raisonnables
    if "has_burn" in token_data or "tax_percent" in token_data:
        criteria += 1
        if token_data.get("has_burn", False) or token_data.get("tax_percent", 0) <= 2:
            score += 1

    # ✅ Projet ancien (> 6 mois)
    if "age_days" in token_data:
        criteria += 1
        if token_data["age_days"] >= 180:
            score += 1

    # Normalisation
    if criteria == 0:
        return 0.0

    return round(score / criteria, 2)


def score_tokens(token_list):
    """
    Applique le scoring éthique à une liste de tokens et sauvegarde les résultats.

    Args:
        token_list (list of dict): Liste des tokens avec leurs métadonnées.
    
    Returns:
        dict: Dictionnaire {symbol: ethic_score}
    """
    result = {}
    for token in token_list:
        symbol = token.get("symbol", "UNKNOWN")
        score = compute_ethic_score(token)
        result[symbol] = score

    # Sauvegarde dans un fichier JSON
    with open(ETHIC_SCORE_LOG, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Scores éthiques enregistrés dans {ETHIC_SCORE_LOG}")
    return result


# Exemple de test
if __name__ == "__main__":
    sample_tokens = [
        {
            "symbol": "TOKEN1",
            "max_wallet_percent": 4.8,
            "team_allocation_percent": 20,
            "github_activity": True,
            "has_burn": False,
            "tax_percent": 1,
            "age_days": 200
        },
        {
            "symbol": "TOKEN2",
            "max_wallet_percent": 12,
            "team_allocation_percent": 30,
            "github_activity": False,
            "has_burn": False,
            "tax_percent": 3,
            "age_days": 50
        }
    ]
    score_tokens(sample_tokens)