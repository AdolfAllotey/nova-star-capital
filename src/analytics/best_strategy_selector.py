
import pandas as pd

def best_strategy_per_token(historique_csv="data/historique/historique_backtests.csv"):
    try:
        df = pd.read_csv(historique_csv)
    except FileNotFoundError:
        return {}

    summary = {}
    for (token, strategy), group in df.groupby(["token", "strategy"]):
        avg_return = group["return_pct"].mean()
        if token not in summary:
            summary[token] = {}
        summary[token][strategy] = avg_return

    # Select best strategy per token
    best_strategies = {}
    for token, strat_dict in summary.items():
        best = max(strat_dict.items(), key=lambda x: x[1])  # highest avg return
        best_strategies[token] = best[0]

    return best_strategies
