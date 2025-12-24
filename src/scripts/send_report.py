import pandas as pd
import datetime
from src.utils.file_utils import save_report_to_txt
from src.utils.telegram_bot import send_telegram_message
# from src.utils.email_utils import send_email_report  # Désactivé pour la V1

SIMULATION_FILE = "data/simulation/live/simulated_trades_live.csv"

def generate_live_report():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    df = pd.read_csv(SIMULATION_FILE)

    df_today = df[df["datetime"].str.startswith(today)]

    if df_today.empty:
        return "📊 Aucun trade simulé pour aujourd’hui."

    total_profit = df_today["profit"].sum()
    nb_trades = len(df_today)
    trades_pos = df_today[df_today["profit"] > 0]
    trades_neg = df_today[df_today["profit"] <= 0]

    lines = [f"📊 **Résumé Simulation {today}**\n"]
    lines.append(f"Nombre de trades simulés : {nb_trades}")
    lines.append(f"✔️ Trades positifs : {len(trades_pos)}")
    lines.append(f"❌ Trades négatifs : {len(trades_neg)}")
    lines.append(f"💰 Profit total simulé : {total_profit:.2f} $")

    return "\n".join(lines)

def main():
    report = generate_live_report()

    # Sauvegarde locale
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    save_report_to_txt(report, f"data/reports/report_{today_str}.txt")

    # Envoi Telegram
    send_telegram_message(report)

    # Envoi email désactivé pour la V1
    # send_email_report(report, subject=f"Rapport Simulation {today_str}")

if __name__ == "__main__":
    main()