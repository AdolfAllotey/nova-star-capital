
# src/v2/analysis/ethical_scoring.py

def compute_ethical_score(token_data):
    """
    Calcule un score éthique pour chaque token.

    Args:
        token_data (list): Liste de tokens avec leurs métadonnées. Chaque token est un dict contenant :
            - token (str)
            - decentralized (bool)
            - dev_wallet_percent (float)
            - github_commits_per_month (int)
            - blacklisted (bool)
            - allocation_transparency (bool)

    Returns:
        list: Liste de dicts avec le token et son score éthique.
    """
    results = []

    for token in token_data:
        score = 100
        reasons = []

        # Décentralisation
        if not token.get("decentralized", False):
            score -= 20
            reasons.append("Centralisé")

        # Dev wallet concentration
        dev_percent = token.get("dev_wallet_percent", 0)
        if dev_percent > 20:
            score -= 25
            reasons.append(f"Dev >20% ({dev_percent}%)")
        elif dev_percent > 10:
            score -= 10
            reasons.append(f"Dev >10% ({dev_percent}%)")

        # Github activité
        commits = token.get("github_commits_per_month", 0)
        if commits < 5:
            score -= 15
            reasons.append("GitHub inactif")
        elif commits < 20:
            score -= 5
            reasons.append("GitHub peu actif")

        # Transparence
        if not token.get("allocation_transparency", False):
            score -= 10
            reasons.append("Pas de transparence")

        # Blacklist
        if token.get("blacklisted", False):
            score = 0
            reasons.append("Blacklisté")

        # Note finale
        status = "green"
        if score < 40:
            status = "red"
        elif score < 70:
            status = "neutral"

        results.append({
            "token": token["token"],
            "ethical_score": score,
            "status": status,
            "reasons": reasons
        })

    return results

# Exemple de test
if __name__ == "__main__":
    test_tokens = [
        {
            "token": "BTC", "decentralized": True, "dev_wallet_percent": 0,
            "github_commits_per_month": 50, "blacklisted": False,
            "allocation_transparency": True
        },
        {
            "token": "SHADY", "decentralized": False, "dev_wallet_percent": 25,
            "github_commits_per_month": 2, "blacklisted": True,
            "allocation_transparency": False
        }
    ]

    scores = compute_ethical_score(test_tokens)
    for s in scores:
        print(s)
