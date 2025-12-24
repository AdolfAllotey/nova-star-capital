import os
import csv
from datetime import datetime

HISTORIQUE_PATH = "data/historique/historique_backtests.csv"
os.makedirs(os.path.dirname(HISTORIQUE_PATH), exist_ok=True)

def append_to_historique(data):
    """
    Ajoute une ligne dans l'historique des backtests.
    :param data: dict contenant les champs suivants :
        source, strategy, token, timeframe, start_date, end_date,
        return_pct, nb_trades, win_rate_pct
    """
    file_exists = os.path.exists(HISTORIQUE_PATH)
    with open(HISTORIQUE_PATH, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "date_backtest", "source", "strategy", "token", "timeframe",
            "start_date", "end_date", "return_pct", "nb_trades", "win_rate_pct"
        ])
        if not file_exists:
            writer.writeheader()

        data_row = data.copy()
        data_row["date_backtest"] = datetime.now().isoformat()
        writer.writerow(data_row)