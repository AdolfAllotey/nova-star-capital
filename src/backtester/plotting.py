import os
import matplotlib.pyplot as plt

def plot_backtest(df, strategy_name="rsi", config=None):
    """
    Affiche et sauvegarde deux graphiques :
    - Le prix avec signaux
    - Le RSI
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    # --- Prix ---
    ax1.plot(df["close"], label="Prix de clôture", color="black", linewidth=1)
    ax1.scatter(df[df["signal"] == 1].index, df[df["signal"] == 1]["close"], marker="^", color="green", label="Achat")
    ax1.scatter(df[df["signal"] == -1].index, df[df["signal"] == -1]["close"], marker="v", color="red", label="Vente")
    ax1.set_title(f"Backtest {strategy_name.upper()}")
    ax1.set_ylabel("Prix")
    ax1.legend()
    ax1.grid(True)

    # --- RSI ---
    if "rsi" in df.columns:
        ax2.plot(df["rsi"], label="RSI", color="blue")
        ax2.axhline(70, color="red", linestyle="--", linewidth=1, label="Sur-achat (70)")
        ax2.axhline(30, color="green", linestyle="--", linewidth=1, label="Sur-vente (30)")
        ax2.set_ylabel("RSI")
        ax2.set_xlabel("Date")
        ax2.legend()
        ax2.grid(True)
    else:
        ax2.text(0.5, 0.5, "RSI non disponible", ha='center', va='center')
        ax2.axis('off')

    plt.tight_layout()

    # --- Enregistrement automatique ---
    if config:
        symbol = config["symbol"].replace("/", "")
        timeframe = config["timeframe"]
        start = config["start_date"]
        end = config["end_date"]

        output_dir = os.path.join("charts")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{strategy_name}_{symbol}_{timeframe}_{start}_{end}.png"
        filepath = os.path.join(output_dir, filename)

        plt.savefig(filepath)
        print(f"🖼️ Graphique sauvegardé dans : {filepath}")

    plt.show()