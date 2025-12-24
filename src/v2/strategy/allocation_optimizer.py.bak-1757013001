
import pandas as pd

def optimize_allocation(tokens, base_amount=1000):
    """
    Calcule une allocation pondérée pour chaque token en fonction du score et du sentiment.

    Args:
        tokens (list): Liste de tokens avec 'symbol', 'score', 'sentiment'.
        base_amount (float): Montant de base à répartir.

    Returns:
        list: Liste des allocations par token avec montant final.
    """
    df = pd.DataFrame(tokens)

    if df.empty or "score" not in df.columns or "sentiment" not in df.columns:
        return []

    # Normalisation des scores et sentiments (0-1)
    df["score_norm"] = df["score"] / df["score"].max()
    df["sentiment_norm"] = df["sentiment"] / 1.0  # déjà entre 0 et 1

    # Pondération simple : moyenne des deux
    df["weight"] = (df["score_norm"] + df["sentiment_norm"]) / 2
    df["weight"] = df["weight"] / df["weight"].sum()

    # Allocation finale
    df["allocated_amount"] = df["weight"] * base_amount

    allocations = df[["symbol", "allocated_amount"]].to_dict(orient="records")
    return allocations

# Exemple d'utilisation
if __name__ == "__main__":
    tokens = [
        {"symbol": "BTC", "score": 90, "sentiment": 0.7},
        {"symbol": "ETH", "score": 85, "sentiment": 0.8},
        {"symbol": "SOL", "score": 70, "sentiment": 0.6}
    ]
    result = optimize_allocation(tokens, base_amount=3000)
    for r in result:
        print(f"{r['symbol']}: {r['allocated_amount']:.2f} €")
