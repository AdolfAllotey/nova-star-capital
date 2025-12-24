import os
import pandas as pd
from datetime import datetime

def score_detected_tokens():
    print("📥 Chargement des données sociales...")
    path = "data/social/tokens_discovered_latest.csv"
    if not os.path.exists(path):
        print(f"❌ Fichier introuvable : {path}")
        return

    df_tokens = pd.read_csv(path)

    print("🧮 Calcul des scores...")
    df_scores = (
        df_tokens.groupby(["symbol", "exchange"])
        .size()
        .reset_index(name="score")
        .sort_values("score", ascending=False)
    )

    print(f"✅ {len(df_scores)} token(s) détecté(s)")
    print("🏆 Top 10 :")
    print(df_scores.head(10))

    print("\n📈 Répartition par plateforme :")
    print(df_scores["exchange"].value_counts())

    print(f"\n📦 Score cumulé : {df_scores['score'].sum()}")

    # Sauvegarde avec horodatage
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "data/social"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"social_detected_tokens_ranked_{now}.csv")
    latest_path = os.path.join(output_dir, "social_detected_tokens_ranked_latest.csv")

    df_scores.to_csv(output_path, index=False)

    if os.path.islink(latest_path) or os.path.exists(latest_path):
        os.remove(latest_path)
    os.symlink(os.path.basename(output_path), latest_path)

    print(f"\n💾 Fichier exporté : {output_path}")
    print(f"🔗 Lien symbolique mis à jour : {latest_path} → {output_path}")

def main():
    score_detected_tokens()

__all__ = ["score_detected_tokens", "main"]

if __name__ == "__main__":
    main()