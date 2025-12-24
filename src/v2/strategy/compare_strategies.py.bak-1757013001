
import os
import pandas as pd
import matplotlib.pyplot as plt

BACKTEST_DIR = "data/v2/backtests"
PLOT_DIR = "data/v2/plots"
os.makedirs(PLOT_DIR, exist_ok=True)

def load_backtest_results():
    """
    Charge tous les fichiers de backtest dans le dossier et les concatène.
    """
    all_dfs = []
    for file in os.listdir(BACKTEST_DIR):
        if file.endswith(".csv"):
            df = pd.read_csv(os.path.join(BACKTEST_DIR, file))
            all_dfs.append(df)
    return pd.concat(all_dfs, ignore_index=True)

def compare_strategies(df: pd.DataFrame):
    """
    Calcule les PnL cumulés par stratégie et affiche les courbes.
    """
    df["date"] = pd.to_datetime(df["date"])
    grouped = df.groupby(["date", "strategy"])["pnl"].sum().reset_index()
    pivot = grouped.pivot(index="date", columns="strategy", values="pnl").fillna(0)
    cumulative = pivot.cumsum()

    # Tracé
    plt.figure(figsize=(12, 6))
    for column in cumulative.columns:
        plt.plot(cumulative.index, cumulative[column], label=column)

    plt.title("Comparaison des stratégies – PnL cumulés")
    plt.xlabel("Date")
    plt.ylabel("PnL cumulés (€)")
    plt.legend()
    plt.grid(True)

    plot_path = os.path.join(PLOT_DIR, "strategy_comparison.png")
    plt.savefig(plot_path)
    print(f"✅ Graphe sauvegardé : {plot_path}")
    return plot_path

# Exemple d'utilisation
if __name__ == "__main__":
    df_all = load_backtest_results()
    compare_strategies(df_all)
