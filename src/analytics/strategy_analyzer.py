
import pandas as pd

def analyze_strategy_performance(historique_csv="data/historique/historique_backtests.csv"):
    try:
        df = pd.read_csv(historique_csv)
    except FileNotFoundError:
        return {"error": "historique_backtests.csv not found."}

    summary = {}

    for strategy, group in df.groupby("strategy"):
        avg_return = group["return_pct"].mean()
        win_rate = (group["return_pct"] > 0).sum() / len(group) * 100
        nb_trades = group["nb_trades"].sum()

        summary[strategy] = {
            "avg_return_pct": round(avg_return, 2),
            "win_rate_pct": round(win_rate, 2),
            "nb_trades_total": int(nb_trades),
            "nb_backtests": len(group)
        }

    return summary

def get_best_strategies(summary, top_n=2):
    sorted_strats = sorted(summary.items(), key=lambda x: x[1]["avg_return_pct"], reverse=True)
    return sorted_strats[:top_n]
