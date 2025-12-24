
# src/v2/scoring/ethical_scorer.py

def compute_ethical_score(token_data):
    """
    Calcule un score éthique basé sur quelques règles simples.

    Args:
        token_data (dict): Informations sur le token

    Returns:
        float: Score éthique entre 0.0 (mauvais) et 1.0 (excellent)
    """
    score = 1.0

    # Exemple de règles de pénalisation
    if token_data.get("top_holder_pct", 0) > 5.0:
        score -= 0.3  # trop concentré

    if token_data.get("num_holders", 0) < 100:
        score -= 0.2  # trop peu de holders

    if token_data.get("rug_pull_flag", False):
        score -= 0.5  # flag rug pull

    if not token_data.get("dev_doxxed", True):
        score -= 0.1  # développeurs anonymes

    return max(0.0, min(1.0, round(score, 2)))


# Exemple d’utilisation
if __name__ == "__main__":
    token = {
        "name": "TokenXYZ",
        "top_holder_pct": 12.5,
        "num_holders": 75,
        "rug_pull_flag": True,
        "dev_doxxed": False
    }
    print("🧪 Score éthique :", compute_ethical_score(token))
