
# src/v2/scoring/ethical_filter.py

from src.v2.scoring.ethical_scorer import compute_ethical_score

def apply_ethical_filter(tokens, user_strategy):
    """
    Applique le score éthique aux tokens et filtre selon les préférences utilisateur.

    Args:
        tokens (list of dict): Liste des tokens sélectionnés
        user_strategy (dict): Stratégie utilisateur, ex: {"ethical_filter": true}

    Returns:
        list of dict: Tokens filtrés et enrichis avec le score éthique
    """
    filtered_tokens = []
    for token in tokens:
        score = compute_ethical_score(token)
        token["ethical_score"] = score

        if user_strategy.get("ethical_filter"):
            if score >= 0.5:
                filtered_tokens.append(token)
        else:
            filtered_tokens.append(token)

    return filtered_tokens
