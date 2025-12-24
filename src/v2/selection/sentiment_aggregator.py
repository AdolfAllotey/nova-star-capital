
import pandas as pd

def get_token_sentiment():
    """
    Simule ou agrège le sentiment des tokens à partir de Reddit, Telegram, Twitter.
    Dans la V2, il pourra s’appuyer sur des modèles d’analyse de sentiment.
    """
    # Exemple de sentiments simulés
    data = [
        {"symbol": "BTC", "sentiment": 0.72},
        {"symbol": "ETH", "sentiment": 0.65},
        {"symbol": "SOL", "sentiment": 0.38},
        {"symbol": "PEPE", "sentiment": -0.05}
    ]
    return pd.DataFrame(data)

# Exemple d’utilisation :
# df = get_token_sentiment()
# print(df)
