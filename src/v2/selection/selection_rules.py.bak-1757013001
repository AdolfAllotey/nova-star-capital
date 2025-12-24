
import pandas as pd

def apply_selection_rules(df: pd.DataFrame, min_score=0.6, min_sentiment=0.2):
    """
    Applique les règles de filtrage pour sélectionner les meilleurs tokens :
    - Score >= min_score
    - Sentiment >= min_sentiment
    """
    selected = df[
        (df["score"] >= min_score) &
        (df["sentiment"] >= min_sentiment)
    ].copy()

    # Optionnel : trier par score ou sentiment
    selected = selected.sort_values(by=["score", "sentiment"], ascending=False)

    return selected

# Exemple d’utilisation :
# from token_screener import screen_tokens
# df_all = screen_tokens()
# df_selected = apply_selection_rules(df_all)
