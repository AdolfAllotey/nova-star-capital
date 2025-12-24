import pandas as pd
from datetime import datetime
import os

def merge_results_and_decide(score_file=None, sentiment_file=None, output_folder="data/social"):
    # Utilisation des derniers fichiers si non spécifiés
    if score_file is None:
        score_file = os.path.join(output_folder, "social_detected_tokens_ranked.csv")
    if sentiment_file is None:
        files = [f for f in os.listdir(output_folder) if f.startswith("social_token_sentiment_")]
        if not files:
            raise FileNotFoundError("Aucun fichier de sentiment trouvé.")
        latest_file = sorted(files)[-1]
        sentiment_file = os.path.join(output_folder, latest_file)

    print(f"📥 Chargement :\n  - Scores : {score_file}\n  - Sentiment : {sentiment_file}")

    df_score = pd.read_csv(score_file)
    df_sentiment = pd.read_csv(sentiment_file)

    # Fusion sur le symbole (clé unique)
    df_merged = pd.merge(df_score, df_sentiment, on="symbol", how="left")

    # Ajout d'un score combiné (pondéré ici comme exemple)
    df_merged["combined_score"] = df_merged["score"] * (1 + df_merged["sentiment"].fillna(0))

    # Tri décroissant
    df_sorted = df_merged.sort_values(by="combined_score", ascending=False)

    # Top tokens à surveiller
    top_tokens = df_sorted[df_sorted["combined_score"] > 10].head(10)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_folder, f"merged_token_summary_{now_str}.csv")
    top_file = os.path.join(output_folder, f"top_token_opportunities_{now_str}.csv")

    df_sorted.to_csv(output_file, index=False)
    top_tokens.to_csv(top_file, index=False)

    print(f"✅ Résultat fusionné : {output_file}")
    print(f"🏆 Top tokens exportés : {top_file}")
    return df_sorted, top_tokens

if __name__ == "__main__":
    merge_results_and_decide()