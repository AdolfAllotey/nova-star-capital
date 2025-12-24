
# src/v2/core/dynamic_allocator.py

def compute_allocation(tokens, config):
    """
    Calcule les montants à investir par token en fonction du score et du sentiment.

    Args:
        tokens (list): Liste de dicts contenant les clés 'token', 'score' et 'sentiment'.
        config (dict): Dictionnaire contenant les pondérations et le capital à investir.

    Returns:
        list: Liste de dicts avec 'token' et 'amount' alloué.
    """
    score_weight = config.get("score_weight", 0.5)
    sentiment_weight = config.get("sentiment_weight", 0.5)
    total_capital = config.get("capital_to_invest", 1000)

    # Calcul du poids combiné pour chaque token
    for token in tokens:
        s = token.get("score", 0)
        sent = token.get("sentiment", 0)
        token["combined_weight"] = score_weight * s + sentiment_weight * sent

    total_weight = sum(t["combined_weight"] for t in tokens if t["combined_weight"] > 0)

    if total_weight == 0:
        print("⚠️ Aucune pondération positive, allocation impossible.")
        return []

    # Allocation proportionnelle
    allocation = []
    for token in tokens:
        weight = token["combined_weight"]
        if weight > 0:
            amount = (weight / total_weight) * total_capital
            allocation.append({
                "token": token["token"],
                "amount": round(amount, 2),
                "score": token["score"],
                "sentiment": token["sentiment"]
            })

    return allocation

# Exemple de test
if __name__ == "__main__":
    tokens = [
        {"token": "BTC", "score": 90, "sentiment": 0.8},
        {"token": "ETH", "score": 85, "sentiment": 0.75},
        {"token": "XRP", "score": 60, "sentiment": 0.4},
    ]
    config = {
        "score_weight": 0.7,
        "sentiment_weight": 0.3,
        "capital_to_invest": 1500
    }
    result = compute_allocation(tokens, config)
    for r in result:
        print(r)
