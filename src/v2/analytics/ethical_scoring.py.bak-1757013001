
# src/v2/analytics/ethical_scoring.py

import random

# ✅ Ce module est un exemple simplifié. Il sera enrichi plus tard avec des données réelles (tokenomics, audits, etc.)

def compute_ethical_score(token_data):
    """
    Calcule un score éthique pour un token basé sur quelques critères simulés.

    Args:
        token_data (dict): Dictionnaire contenant des informations sur le token.

    Returns:
        float: Score éthique entre 0 et 1.
    """
    score = 0

    # 🧮 Critères simulés (à remplacer par de vraies données plus tard)
    top_wallets_pct = token_data.get("top_wallets_pct", random.uniform(2, 30))  # %
    has_audit = token_data.get("has_audit", random.choice([True, False]))
    is_decentralized = token_data.get("is_decentralized", random.choice([True, False]))
    team_known = token_data.get("team_known", random.choice([True, False]))

    # 🧠 Pondération des critères
    if top_wallets_pct < 5:
        score += 0.3
    elif top_wallets_pct < 10:
        score += 0.2
    elif top_wallets_pct < 20:
        score += 0.1

    if has_audit:
        score += 0.2

    if is_decentralized:
        score += 0.2

    if team_known:
        score += 0.1

    return round(min(score, 1.0), 2)

def score_token_list(token_list):
    """
    Applique le scoring éthique à une liste de tokens.

    Args:
        token_list (list): Liste de dictionnaires avec données token.

    Returns:
        list: Liste enrichie avec le score éthique.
    """
    for token in token_list:
        token["ethical_score"] = compute_ethical_score(token)
    return token_list

# Exemple d'utilisation
if __name__ == "__main__":
    sample_tokens = [
        {"symbol": "ABC", "top_wallets_pct": 3.5, "has_audit": True, "is_decentralized": True, "team_known": True},
        {"symbol": "XYZ", "top_wallets_pct": 22.0, "has_audit": False, "is_decentralized": False, "team_known": False},
    ]

    scored = score_token_list(sample_tokens)
    for token in scored:
        print(f"{token['symbol']} ➜ Ethical Score : {token['ethical_score']}")
