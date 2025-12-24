
import pandas as pd

def get_token_scores():
    """
    Simule ou calcule les scores des tokens.
    Dans la V2, ce module pourra combiner volume, momentum, trend, engagement, etc.
    """
    # Exemple de données simulées pour test
    data = [
        {"symbol": "BTC", "score": 0.87},
        {"symbol": "ETH", "score": 0.79},
        {"symbol": "SOL", "score": 0.55},
        {"symbol": "PEPE", "score": 0.12}
    ]
    return pd.DataFrame(data)

# Exemple d'utilisation :
# df = get_token_scores()
# print(df)
