import os
import pandas as pd
import plotly.express as px

def main():
    report_path = os.path.join("reports", "best_strategies_only.csv")
    if not os.path.exists(report_path):
        print(f"❌ Fichier introuvable : {report_path}")
        return

    df = pd.read_csv(report_path)
    if df.empty:
        print("⚠️ Le fichier est vide.")
        return

    print("✅ Chargement OK — génération HTML interactive...")

    df["label"] = df["symbol"] + " " + df["timeframe"]

    fig = px.bar(
        df,
        x="label",
        y="total_return_%",
        color="stratégie",
        color_discrete_map={"EMA": "blue", "RSI": "orange"},
        hover_data=["nb_trades", "win_rate_%", "paramètres"],
        title="📊 Meilleure stratégie par actif et timeframe (interactive)",
        labels={"total_return_%": "Rendement (%)", "label": "Actif / Timeframe"},
    )

    fig.update_layout(xaxis_tickangle=-45)

    os.makedirs("charts/compare", exist_ok=True)
    out_path = os.path.join("charts", "compare", "best_strategies_interactive.html")
    fig.write_html(out_path)

    print(f"🌐 Graphique interactif sauvegardé : {out_path}")
    print("✅ Ouvre-le dans ton navigateur !")

if __name__ == "__main__":
    main()