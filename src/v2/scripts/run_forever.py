
import time
from datetime import datetime, timezone, timezone
from src.v2.utils.retry_handler import retry_on_failure
from src.v2.trading.trade_simulator import run_trade_simulation
from src.v2.trading.position_tracker import track_positions
from src.v2.reporting.report_generator import generate_summary_report
from src.v2.reporting import save_report, send_report_via_telegram

@retry_on_failure()
def daily_simulation_cycle():
    print(f"🔁 Nouvelle exécution à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Simulation des trades
    trades = run_trade_simulation()

    # 2. Suivi des positions et PnL
    if trades:
        performance = track_positions()

        # 3. Génération du rapport consolidé
        report = generate_summary_report()
        report_path = save_report(report)

        # 4. Envoi du rapport
        send_report_via_telegram(report)
        # send_report_via_email(report, report_path)  # Optionnel

        print("✅ Cycle quotidien terminé.")
    else:
        print("❌ Aucun trade simulé. Cycle ignoré.")

def run_forever(interval_hours=24):
    while True:
        daily_simulation_cycle()
        print(f"⏳ Pause pendant {interval_hours}h...
")
        time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    run_forever()
