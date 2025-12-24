import os
import pandas as pd
from datetime import datetime
from social.detect_tokens_from_social import detect_tokens

def main():
    print("📥 Chargement des données sociales...")
    combined_path = "data/social/social_combined_posts_latest.csv"
    df = pd.read_csv(combined_path)

    print("🔎 Détection des tokens...")
    # Appel de la fonction en passant explicitement le DataFrame
    detected = detect_tokens(df=df)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "data/social"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/tokens_discovered_{now}.csv"
    detected.to_csv(output_path, index=False)

    # Création ou mise à jour du lien symbolique
    symlink_path = f"{output_dir}/tokens_discovered_latest.csv"
    if os.path.islink(symlink_path) or os.path.exists(symlink_path):
        os.remove(symlink_path)
    os.symlink(os.path.basename(output_path), symlink_path)

    print(f"✅ Tokens sauvegardés dans {output_path}")
    print(f"🔗 Lien symbolique mis à jour : {symlink_path} → {output_path}")

if __name__ == "__main__":
    main()