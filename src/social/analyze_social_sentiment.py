import os
import pandas as pd
from datetime import datetime
from textblob import TextBlob

def analyze_social_sentiment():
    path = "data/social/social_combined_posts_latest.csv"
    print(f"📥 Lecture des données depuis {path}")
    
    if not os.path.exists(path):
        print(f"❌ Fichier introuvable : {path}")
        return

    df = pd.read_csv(path)

    # Vérification des colonnes
    missing_cols = []
    for col in ["token", "text"]:
        if col not in df.columns:
            missing_cols.append(col)

    if missing_cols:
        print(f"❌ Colonnes manquantes : {', '.join(missing_cols)}")
        print("💡 Assurez-vous que chaque post possède une colonne 'text' et que les tokens ont été attribués.")
        return

    if df["token"].isna().all():
        print("❌ Aucune valeur dans la colonne 'token'.")
        return

    print(f"🔍 Analyse de sentiment sur {df['token'].nunique()} tokens...")

    results = []
    for token, group in df.groupby("token"):
        if token is None or pd.isna(token): continue
        sentiments = [TextBlob(str(text)).sentiment.polarity for text in group["text"]]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        results.append({
            "token": token,
            "mentions": len(group),
            "avg_sentiment": avg_sentiment
        })

    df_result = pd.DataFrame(results).sort_values(by="avg_sentiment", ascending=False)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "data/social"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/social_token_sentiment_{now}.csv"
    latest_symlink = f"{output_dir}/social_token_sentiment_latest.csv"

    df_result.to_csv(output_path, index=False)

    if os.path.exists(latest_symlink) or os.path.islink(latest_symlink):
        os.remove(latest_symlink)
    os.symlink(os.path.abspath(output_path), latest_symlink)

    print(f"✅ Analyse terminée pour {len(df_result)} tokens.")
    print(f"💾 Sentiments sauvegardés dans {output_path}")
    print(f"🔗 Lien symbolique mis à jour : {latest_symlink} → {output_path}")

def main():
    analyze_social_sentiment()

__all__ = ["analyze_social_sentiment", "main"]

if __name__ == "__main__":
    main()