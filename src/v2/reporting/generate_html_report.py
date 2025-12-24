# src/v2/reporting/generate_html_report.py

import os
import json
from datetime import datetime, timezone, timezone
from src.v2.utils.logger import get_logger
from src.v2.utils.telegram_utils import send_telegram_message

logger = get_logger("generate_html_report")

SIMULATION_FOLDER = "src/v2/data/simulation"
REPORT_FOLDER = "src/v2/data/reports"
SUMMARY_FILE = "src/v2/data/llm/summary.txt"  # optionnel

HTML_TEMPLATE = """
<html>
<head>
    <meta charset="UTF-8">
    <title>Rapport du {date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pnl-positive {{ color: green; }}
        .pnl-negative {{ color: red; }}
    </style>
</head>
<body>
    <h1>📊 Rapport du {date}</h1>

    <h2>Performance simulée</h2>
    <table>
        <tr><th>Token</th><th>Entrée</th><th>Sortie</th><th>PNL</th><th>Résultat</th></tr>
        {rows}
    </table>

    {summary_section}
</body>
</html>
"""

def load_simulation(date_str):
    file_path = os.path.join(SIMULATION_FOLDER, f"{date_str}_simulated_trades.json")
    if not os.path.exists(file_path):
        logger.error(f"❌ Fichier de simulation introuvable : {file_path}")
        return []
    with open(file_path, "r") as f:
        return json.load(f)

def load_summary():
    if not os.path.exists(SUMMARY_FILE):
        return ""
    with open(SUMMARY_FILE, "r") as f:
        return f.read()

def generate_html(date_str):
    trades = load_simulation(date_str)
    rows_html = ""
    for trade in trades:
        pnl_class = "pnl-positive" if trade["pnl"] >= 0 else "pnl-negative"
        rows_html += f"<tr><td>{trade['token']}</td><td>{trade['entry_price']}</td><td>{trade['exit_price']}</td><td class='{pnl_class}'>{trade['pnl']} €</td><td>{trade['outcome']}</td></tr>\n"

    summary = load_summary()
    summary_section = f"<h2>🧠 Résumé LLM</h2><p>{summary}</p>" if summary else ""

    html = HTML_TEMPLATE.format(date=date_str, rows=rows_html, summary_section=summary_section)
    output_path = os.path.join(REPORT_FOLDER, f"{date_str}_report.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"✅ Rapport HTML sauvegardé dans : {output_path}")
    return output_path

def main():
    date_str = os.getenv("FAKE_DATE") or datetime.now().strftime("%Y-%m-%d")
    path = generate_html(date_str)

    # Optionnel : notifier sur Telegram
    try:
        send_telegram_message(f"✅ Rapport HTML généré pour {date_str} :\n{path}")
    except Exception as e:
        logger.warning(f"Erreur envoi Telegram : {e}")

if __name__ == "__main__":
    main()
