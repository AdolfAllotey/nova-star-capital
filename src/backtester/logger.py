import csv
import os
from datetime import datetime

def log_backtest_result(strategy, config, results):
    """
    Enregistre un résumé de chaque backtest dans logs/backtest_log.csv
    """
    os.makedirs("logs", exist_ok=True)
    log_file = "logs/backtest_log.csv"

    # Déterminer si c'est le premier enregistrement
    is_new = not os.path.exists(log_file)

    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow([
                "datetime",
                "strategy",
                "symbol",
                "timeframe",
                "start_date",
                "end_date",
                "total_return_%",
                "nb_trades",
                "win_rate_%"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            strategy,
            config.get("symbol", ""),
            config.get("timeframe", ""),
            config.get("start_date", ""),
            config.get("end_date", ""),
            results.get("total_return_%", ""),
            results.get("nb_trades", ""),
            results.get("win_rate_%", "")
        ])