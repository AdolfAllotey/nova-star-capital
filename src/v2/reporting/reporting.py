import os
import json
from datetime import datetime, timezone, timezone
from src.utils.telegram_bot import send_telegram_message
from src.utils.email_utils import send_email  # Assure-toi que cette fonction existe et accepte les bons paramètres

REPORTS_FOLDER = "data/v2/reports"
os.makedirs(REPORTS_FOLDER, exist_ok=True)

def save_report(report_data, report_name=None):
    if report_name is None:
        report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join(REPORTS_FOLDER, report_name)
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"✅ Rapport sauvegardé : {report_path}")
    return report_path

def generate_daily_report(trades, performance, alerts):
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "trades": trades,
        "performance": performance,
        "alerts": alerts
    }
    return report

def send_report_via_telegram(report):
    message = f"📊 Rapport quotidien - {report['date']}\n"
    message += f"Trades: {len(report['trades'])} transactions\n"
    message += f"Performance: {report['performance']}\n"
    if report['alerts']:
        message += f"⚠️ Alertes: {len(report['alerts'])}\n"
    else:
        message += "✅ Aucune alerte\n"
    send_telegram_message(message)

def send_report_via_email(report, recipient_email, attach_file=True):
    subject = f"Rapport quotidien - {report['date']}"
    body = (
        f"Bonjour,\n\nVoici le rapport quotidien.\n\n"
        f"Trades effectués : {len(report['trades'])}\n"
        f"Performance : {report['performance']}\n"
        f"Alertes : {len(report['alerts']) if report['alerts'] else 'Aucune'}\n\n"
        f"Cordialement,\nVotre Bot Crypto"
    )
    attachment_path = None
    if attach_file:
        attachment_path = save_report(report, f"daily_report_{report['date']}.json")

    send_email(
        to=recipient_email,
        subject=subject,
        body=body,
        attachment=attachment_path
    )

    if attachment_path and os.path.exists(attachment_path):
        os.remove(attachment_path)

if __name__ == "__main__":
    # Exemple simple de test
    sample_trades = [
        {"symbol": "BTC", "action": "buy", "qty": 0.1, "price": 30000},
        {"symbol": "ETH", "action": "sell", "qty": 1, "price": 2000}
    ]
    sample_performance = {"total_pnl": 500.0, "roi_pct": 3.5}
    sample_alerts = ["Stop loss déclenché sur ETH", "Alerte sur BTC"]

    report = generate_daily_report(sample_trades, sample_performance, sample_alerts)
    save_report(report)
    send_report_via_telegram(report)
    # Pour tester l'envoi email, décommente la ligne suivante et ajuste l'email
    # send_report_via_email(report, recipient_email="ton.email@example.com", attach_file=True)