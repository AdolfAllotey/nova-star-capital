import os
import json
import random
from datetime import datetime, timezone, timezone
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import save_json_with_timestamp, load_selected_tokens

logger = get_logger("trade_simulator")

# Configuration
SIMULATED_INVESTMENT_PER_TOKEN = 100  # en USDT
STOP_LOSS_PCT = -0.10
TAKE_PROFIT_PCT = 0.20

def simulate_trade(entry_price, amount_usdt):
    """
    Simule un trade avec SL/TP à partir d'un prix d'entrée.
    """
    sl_price = entry_price * (1 + STOP_LOSS_PCT)
    tp_price = entry_price * (1 + TAKE_PROFIT_PCT)
    outcome = random.choices(['tp', 'sl', 'neutral'], weights=[0.4, 0.3, 0.3])[0]

    if outcome == 'tp':
        exit_price = tp_price
    elif outcome == 'sl':
        exit_price = sl_price
    else:
        exit_price = entry_price * random.uniform(0.95, 1.05)

    pnl = ((exit_price - entry_price) / entry_price) * amount_usdt
    return round(entry_price, 4), round(exit_price, 4), round(pnl, 2), outcome

def run_trade_simulation():
    """
    Lance la simulation sur les tokens sélectionnés du jour.
    """
    selected_tokens = load_selected_tokens()
    if not selected_tokens:
        logger.warning("❌ Aucune sélection de token disponible pour aujourd'hui.")
        return []

    simulated_trades = []
    for token in selected_tokens:
        mock_price = random.uniform(0.5, 50)  # À remplacer plus tard par un vrai prix
        entry_price, exit_price, pnl, outcome = simulate_trade(mock_price, SIMULATED_INVESTMENT_PER_TOKEN)

        simulated_trades.append({
            "token": token,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "outcome": outcome
        })

    output_path = save_json_with_timestamp(
        simulated_trades,
        folder="data/v2/simulation",
        prefix="simulated_trades"
    )

    logger.info(f"✅ Simulation terminée. Résultats sauvegardés dans : {output_path}")
    return simulated_trades