import os
import pandas as pd
from social.utils.token_utils import extract_token_symbols
from pathlib import Path
from datetime import datetime

def detect_tokens(df: pd.DataFrame = None, input_path="data/social/social_combined_posts_latest.csv") -> pd.DataFrame:
    """Détecte les tokens dans un DataFrame ou depuis un fichier CSV."""
    if df is None:
        print("📥 Chargement des données sociales depuis le fichier...")
        df = pd.read_csv(input_path)
    else:
        print("📥 Données sociales reçues en argument.")

    print("🔎 Détection des tokens...")
    texts = df["text"].fillna("").tolist()
    tokens = extract_token_symbols(texts)

    df_tokens = pd.DataFrame(tokens, columns=["symbol"])
    df_tokens["exchange"] = "Unknown"
    df_tokens["score"] = 0

    # Ajout d'une colonne 'token' (1er token détecté par ligne)
    df["token"] = df["text"].apply(lambda t: next(
        (tok for tok in extract_token_symbols([t])), None))

    # Sauvegarde du fichier combiné enrichi
    output_combined_path = Path(input_path)
    df.to_csv(output_combined_path, index=False)
    print(f"✅ Colonne 'token' ajoutée à {output_combined_path}")

    return df_tokens

def detect_tokens_from_texts():
    """Pipeline exportable principal"""
    df_tokens = detect_tokens()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("data/social")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"tokens_discovered_{timestamp}.csv"
    df_tokens.to_csv(output_path, index=False)

    latest_symlink = output_dir / "tokens_discovered_latest.csv"
    if latest_symlink.exists() or latest_symlink.is_symlink():
        latest_symlink.unlink()
    latest_symlink.symlink_to(output_path.resolve())

    print(f"✅ Tokens sauvegardés dans {output_path}")
    print(f"🔗 Lien symbolique mis à jour : {latest_symlink} → {output_path.name}")

def main():
    detect_tokens_from_texts()

__all__ = ["detect_tokens", "detect_tokens_from_texts", "main"]

if __name__ == "__main__":
    main()