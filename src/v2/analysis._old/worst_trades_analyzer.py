import os
from datetime import datetime, timezone, timezone

from src.v2.utils.file_utils import (
    get_logger,
    load_json_file,
    save_json_file,
    ensure_directory_exists,
)

# chemins
SIM_TRADES = "src/v2/data/simulation/trade_simulation.json"
RISK_DIR   = "src/v2/data/risk"
WORST_OUT  = os.path.join(RISK_DIR, "worst_trades.json")

logger = get_logger("worst_trades_analyzer")

def _has_loss_fields(t: dict) -> bool:
    """
    Heuristique : un trade est éligible si on dispose d'infos de résultat.
    Ici on cherche des champs typiques : 'pnl', 'profit', 'return', 'roi'.
    """
    for k in ("pnl", "profit", "return", "roi"):
        if k in t:
            return True
    return False

def _is_loss(t: dict) -> bool:
    """
    Considère 'pnl' < 0, 'profit' < 0, 'return' < 0 ou 'roi' < 0 comme perte.
    S’il n’y a aucune info, on renvoie False (pas de conclusion).
    """
    for k in ("pnl", "profit", "return", "roi"):
        if k in t:
            try:
                return float(t[k]) < 0
            except Exception:
                pass
    return False

def analyze_worst_trades():
    logger.info("🔎 Analyse des pires trades…")

    # charge les trades simulés (ou []) sans lever d’exception
    trades = load_json_file(SIM_TRADES, default=[])
    if not trades:
        logger.warning("⚠️ Aucun trade simulé trouvé, pire trades = [].")
        ensure_directory_exists(WORST_OUT)
        save_json_file(WORST_OUT, [])
        return []

    # Filtre seulement si on a des champs de perte; sinon => aucun pire trade
    eligible = [t for t in trades if _has_loss_fields(t)]
    if not eligible:
        logger.info("ℹ️ Aucune info de PnL/retour dans les trades — aucun pire trade pour l’instant.")
        ensure_directory_exists(WORST_OUT)
        save_json_file(WORST_OUT, [])
        return []

    # Garde uniquement les pertes
    worst = [t for t in eligible if _is_loss(t)]
    # Trie par PnL croissant si dispo (les plus négatifs d’abord)
    def loss_key(t):
        for k in ("pnl", "profit", "return", "roi"):
            if k in t:
                try:
                    return float(t[k])
                except Exception:
                    pass
        return 0.0
    worst.sort(key=loss_key)

    # Optionnel : limite le volume (ex: top 20 pires)
    worst = worst[:20]

    ensure_directory_exists(WORST_OUT)
    save_json_file(WORST_OUT, worst)
    logger.info(f"✅ Pires trades sauvegardés ({len(worst)}) → {WORST_OUT}")
    return worst

if __name__ == "__main__":
    analyze_worst_trades()