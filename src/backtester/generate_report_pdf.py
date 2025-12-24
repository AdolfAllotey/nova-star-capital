import os
import pandas as pd
from fpdf import FPDF
from datetime import datetime

def main():
    csv_path = os.path.join("reports", "best_strategies_only.csv")
    chart_path = os.path.join("charts", "compare", "best_strategies_barplot.png")
    out_path = os.path.join("reports", "backtest_summary.pdf")

    if not os.path.exists(csv_path) or not os.path.exists(chart_path):
        print("❌ Données ou graphique manquants. Lance les étapes précédentes d’abord.")
        return

    df = pd.read_csv(csv_path)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Rapport de Backtest - Stratégies Optimales", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

    # 🔍 Résumé des meilleures stratégies
    pdf.ln(5)
    for _, row in df.iterrows():
        txt = f"{row['symbol']} {row['timeframe']} - {row['stratégie']} : {row['total_return_%']}% | Trades: {row['nb_trades']} | Win rate: {row.get('win_rate_%', '')}%"
        pdf.multi_cell(0, 8, txt)

    # 🖼️ Ajouter le graphique
    pdf.ln(10)
    pdf.image(chart_path, x=15, w=180)

    pdf.output(out_path)
    print(f"✅ Rapport PDF généré : {out_path}")

if __name__ == "__main__":
    main()