import os
import pandas as pd
from datetime import datetime

def main():
    print("📝 Génération du rapport quotidien...")

    # Chargement des scores
    score_path = "data/social/social_detected_tokens_ranked_latest.csv"
    sentiment_path = "data/social/social_token_sentiment_latest.csv"
    report_dir = "data/social"
    simulation_path = "data/simulation/simulated_cumulative_pnl.csv"

    if not os.path.exists(score_path) or not os.path.exists(sentiment_path):
        print("❌ Données de score ou de sentiment manquantes.")
        return

    df_scores = pd.read_csv(score_path)
    df_sentiments = pd.read_csv(sentiment_path)

    # Fusionner pour récap
    merged = pd.merge(df_scores, df_sentiments, how="left", left_on="symbol", right_on="token")
    merged["score_sentiment"] = merged["score"] * merged["avg_sentiment"]

    # Récapitulatif simulation
    sim_summary = ""
    if os.path.exists(simulation_path):
        df_sim = pd.read_csv(simulation_path)
        latest_date = df_sim["date"].max()
        today_trades = df_sim[df_sim["date"] == latest_date]
        daily_pnl = today_trades["pnl"].sum()
        total_pnl = df_sim["pnl"].sum()
        sim_summary = (
            f"\n💸 **Simulation des trades - {latest_date}**\n"
            f"- {len(today_trades)} trades simulés aujourd’hui\n"
            f"- PnL journalier : {daily_pnl:.2f} USDT\n"
            f"- PnL cumulé depuis le début : {total_pnl:.2f} USDT\n"
        )
    else:
        sim_summary = "\n💸 Aucune simulation de trade enregistrée."

    # Générer le rapport
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{report_dir}/social_daily_report_{timestamp}.txt"
    symlink_path = f"{report_dir}/social_daily_report_latest.txt"

    with open(output_path, "w") as f:
        f.write("📊 Rapport quotidien - Analyse des Tokens\n")
        f.write(f"🕒 Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("🏆 Top 10 tokens (score * sentiment) :\n")
        top10 = merged.sort_values("score_sentiment", ascending=False).head(10)
        f.write(top10[["symbol", "score", "avg_sentiment", "score_sentiment"]].to_string(index=False))
        f.write("\n\n")
        f.write(sim_summary)

    # Met à jour le lien symbolique
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(os.path.basename(output_path), symlink_path)

    print(f"✅ Rapport quotidien sauvegardé dans : {output_path}")
    print(f"🔗 Lien symbolique mis à jour : {symlink_path} → {output_path}")

if __name__ == "__main__":
    main()