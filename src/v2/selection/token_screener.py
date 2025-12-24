
import pandas as pd
from src.v2.selection.score_engine import get_token_scores
from src.v2.selection.sentiment_aggregator import get_token_sentiment
from src.v2.monitoring.kol_tracker import get_kol_flags
from src.v2.monitoring.whale_tracker import get_whale_flags
from src.v2.core.blacklist_manager import get_blacklisted_tokens

def screen_tokens():
    # Étape 1 : récupérer les scores, sentiments, signaux KOL/whales
    score_df = get_token_scores()           # DataFrame: symbol | score
    sentiment_df = get_token_sentiment()    # DataFrame: symbol | sentiment
    kol_df = get_kol_flags()                # DataFrame: symbol | kol_flag (bool)
    whale_df = get_whale_flags()            # DataFrame: symbol | whale_flag (bool)
    blacklist = get_blacklisted_tokens()    # Liste ou set de symboles à exclure

    # Étape 2 : fusion des DataFrames sur la colonne 'symbol'
    merged = score_df         .merge(sentiment_df, on="symbol", how="inner")         .merge(kol_df, on="symbol", how="left")         .merge(whale_df, on="symbol", how="left")

    # Étape 3 : nettoyage des valeurs manquantes
    merged["kol_flag"] = merged["kol_flag"].fillna(False)
    merged["whale_flag"] = merged["whale_flag"].fillna(False)

    # Étape 4 : exclusion des tokens blacklistés
    merged = merged[~merged["symbol"].isin(blacklist)]

    return merged

# Exemple d'utilisation :
# df = screen_tokens()
# print(df.head())
