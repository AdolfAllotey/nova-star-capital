import os
import pandas as pd

def analyze_detected_tokens():
    INPUT_CSV = "data/social/social_detected_tokens_latest.csv"

    print("\n📊 Analyse des tokens détectés...")

    # Vérification du fichier
    if not os.path.exists(INPUT_CSV):
        print(f"❌ Fichier introuvable : {INPUT_CSV}")
        return

    # Chargement
    df = pd.read_csv(INPUT_CSV)

    if df.empty:
        print("⚠️ Aucun token détecté.")
        return

    # Tri par score décroissant
    df_sorted = df.sort_values(by="score", ascending=False)

    # Aperçu global
    print(f"✅ {len(df_sorted)} token(s) détecté(s)")
    print("🏆 Top 10 :")
    print(df_sorted.head(10).to_string(index=False))

    # Comptage par exchange
    print("\n📈 Répartition par plateforme :")
    print(df_sorted["exchange"].value_counts().to_string())

    # Score total
    print(f"\n📦 Score cumulé : {df_sorted['score'].sum()}")

    # Export trié
    output_path = "data/social/social_detected_tokens_ranked.csv"
    df_sorted.to_csv(output_path, index=False)
    print(f"\n💾 Fichier exporté : {output_path}")