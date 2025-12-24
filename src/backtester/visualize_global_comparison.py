import os
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

def main():
    report_path = os.path.join("reports", "global_comparison.csv")
    if not os.path.exists(report_path):
        print(f"❌ Fichier introuvable : {report_path}")
        return

    df = pd.read_csv(report_path)
    if df.empty:
        print("⚠️ Le fichier est vide.")
        return

    print("✅ Chargement du fichier réussi.")
    print(df.head())
    print(f"Nombre de lignes : {len(df)}")

    # Créer labels et trier
    df["label"] = df["symbol"] + " " + df["timeframe"] + " (" + df["stratégie"] + ")"
    df = df.sort_values(by="total_return_%", ascending=False)

    print("📊 Préparation du graphique...")

    plt.figure(figsize=(14, 6))
    bars = plt.bar(df["label"], df["total_return_%"],
                   color=["blue" if s == "EMA" else "orange" for s in df["stratégie"]])

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2.0, height,
                 f"{height:.1f}%", ha='center', va='bottom', fontsize=8)

    plt.xticks(rotation=45, ha="right")
    plt.title("Comparaison globale EMA vs RSI")
    plt.ylabel("Total Return (%)")
    plt.tight_layout()

    # Sauvegarde
    os.makedirs("charts/compare", exist_ok=True)
    out_path = os.path.join("charts", "compare", "global_comparison_barplot.png")
    plt.savefig(out_path)
    print(f"📈 Graphique sauvegardé dans : {out_path}")

    plt.show()
    print("✅ Visualisation terminée.")

if __name__ == "__main__":
    main()