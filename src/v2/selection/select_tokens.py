
import os
import pandas as pd
from datetime import datetime, timezone, timezone

from src.v2.selection.token_screener import screen_tokens
from src.v2.selection.selection_rules import apply_selection_rules

def save_selected_tokens(df: pd.DataFrame, folder="src/v2/data/selection"):
    os.makedirs(folder, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_selected_tokens.csv"
    path = os.path.join(folder, filename)
    df.to_csv(path, index=False)
    print(f"✅ Tokens sélectionnés sauvegardés dans : {path}")
    return path

def main():
    print("🔍 Screening des tokens...")
    all_tokens = screen_tokens()

    print("✅ Tokens analysés :", len(all_tokens))

    selected = apply_selection_rules(all_tokens)

    print("🏁 Tokens sélectionnés :", len(selected))
    if not selected.empty:
        save_selected_tokens(selected)
    else:
        print("⚠️ Aucun token sélectionné aujourd'hui.")

if __name__ == "__main__":
    main()
