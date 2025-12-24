import os
import pandas as pd

def main():
    input_path = os.path.join("reports", "global_comparison.csv")
    output_path = os.path.join("reports", "best_strategies_only.csv")

    if not os.path.exists(input_path):
        print(f"❌ Fichier introuvable : {input_path}")
        return

    df = pd.read_csv(input_path)

    if df.empty:
        print("⚠️ Le fichier est vide.")
        return

    print(f"✅ {len(df)} lignes chargées depuis : {input_path}")

    # 🔍 Garder la meilleure stratégie pour chaque (symbol, timeframe)
    grouped = df.sort_values("total_return_%", ascending=False).groupby(["symbol", "timeframe"], as_index=False).first()

    os.makedirs("reports", exist_ok=True)
    grouped.to_csv(output_path, index=False)

    print(f"📊 Résumé des meilleures stratégies enregistré dans : {output_path}")
    print(grouped)

if __name__ == "__main__":
    main()