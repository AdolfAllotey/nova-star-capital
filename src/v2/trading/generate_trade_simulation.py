# src/v2/trading/generate_trade_simulation.py
# Version préprod avec :
# - sélection des tokens via selected_tokens.json
# - garde-fou risk_controller (risk_state.json)
# - sizing basé sur equity + max_position_risk_pct + regime/risk_mode
# - routing exchange via exchange_router

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import List, Dict, Any
import os

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.exchange_router import get_exchange_for_token

log = get_logger("generate_trade_simulation")

# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "src/v2/data")).expanduser().resolve()
SIMULATION_DIR = DATA_DIR / "simulation"
SIMULATION_FILE = SIMULATION_DIR / "trade_simulation.json"

SELECTED_TOKENS_FILE = DATA_DIR / "selected_tokens.json"
RISK_STATE_FILE = DATA_DIR / "reports" / "risk_state.json"


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_selected_tokens() -> List[str]:
    """
    Charge la liste des tokens à simuler depuis selected_tokens.json

    Formats supportés :
      - ["bitcoin", "ethereum", "solana", ...]
      - { "BTC": "BINANCE", "SOL": "MEXC", ... }  -> on prend les clés
    """
    doc = load_json_file(str(SELECTED_TOKENS_FILE), default=[])

    tokens: List[str] = []
    if isinstance(doc, list):
        tokens = [str(t).strip() for t in doc if str(t).strip()]
    elif isinstance(doc, dict):
        tokens = [str(k).strip() for k in doc.keys() if str(k).strip()]

    tokens = [t for t in tokens if t]
    return tokens


def load_risk_gate():
    """
    Lit risk_state.json et renvoie :
      - trading_allowed (bool)
      - regime (str)
      - risk_mode (str)
      - equity_eur (float)
      - limits (dict avec max_position_risk_pct, max_daily_drawdown_pct)
    """
    data = load_json_file(str(RISK_STATE_FILE), default={})

    trading_allowed = bool(data.get("trading_allowed", True))
    regime = data.get("regime", "unknown")
    risk_mode = data.get(
        "effective_risk_mode",
        data.get("upstream_risk_mode", "risk_on"),
    )
    equity = float(data.get("equity_eur", 5000.0))

    limits_raw = data.get("limits") or {}
    max_pos_pct = float(limits_raw.get("max_position_risk_pct", 0.02))
    max_dd_pct = float(limits_raw.get("max_daily_drawdown_pct", 0.08))

    limits = {
        "max_position_risk_pct": max_pos_pct,
        "max_daily_drawdown_pct": max_dd_pct,
    }

    return trading_allowed, regime, risk_mode, equity, limits


# ---------------------------------------------------------------------
# CORE SIZING LOGIC
# ---------------------------------------------------------------------
def compute_position_size(
    equity_eur: float,
    regime: str,
    risk_mode: str,
    limits: Dict[str, float],
) -> float:
    """
    Calcule la taille notionnelle EUR d'une position simulée.

    - On part de max_position_risk_pct (par position) fourni par le risk_controller.
    - On applique un facteur en fonction du régime et du risk_mode :
        * risk_off            -> 0.3 * max_pos_pct
        * regime bear         -> 0.5 * max_pos_pct
        * regime bull + risk_on -> 1.0 * max_pos_pct
        * regime neutral      -> 0.7 * max_pos_pct
        * sinon               -> 0.5 * max_pos_pct
    """
    max_pos_pct = float(limits.get("max_position_risk_pct", 0.02))

    regime = (regime or "").lower()
    risk_mode = (risk_mode or "").lower()

    if risk_mode == "risk_off":
        factor = 0.3
    elif regime == "bear":
        factor = 0.5
    elif regime == "bull" and risk_mode == "risk_on":
        factor = 1.0
    elif regime == "neutral":
        factor = 0.7
    else:
        factor = 0.5

    effective_pct = max_pos_pct * factor
    # sécurité : ne jamais dépasser max_pos_pct
    effective_pct = min(effective_pct, max_pos_pct)

    notional = equity_eur * effective_pct

    log.info(
        "[sizing] equity=%.2f€ max_pos_pct=%.2f%% regime=%s risk_mode=%s "
        "factor=%.2f effective_pct=%.2f%% notional=%.2f€",
        equity_eur,
        max_pos_pct * 100.0,
        regime,
        risk_mode,
        factor,
        effective_pct * 100.0,
        notional,
    )

    return float(round(notional, 2))


# ---------------------------------------------------------------------
# CORE SIMULATION
# ---------------------------------------------------------------------
def simulate_trades() -> List[Dict[str, Any]]:
    log.info("🔄 Démarrage de la simulation des trades")

    # 0) Garde-fou risk_controller
    trading_allowed, regime, risk_mode, equity, limits = load_risk_gate()
    if not trading_allowed:
        log.warning(
            "🚫 Trading bloqué par le risk_controller : regime=%s, risk_mode=%s",
            regime,
            risk_mode,
        )

        SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "server_ts": now_utc_iso(),
            "note": "trading-blocked-by-risk-controller",
            "regime": regime,
            "risk_mode": risk_mode,
            "equity_eur": equity,
            "limits": limits,
            "items": [],
        }
        save_json_file(str(SIMULATION_FILE), payload)
        log.info(
            "📄 trade_simulation.json mis à jour avec un état bloqué → %s",
            SIMULATION_FILE,
        )
        return []

    # 1) Chargement de la liste de tokens
    tokens = load_selected_tokens()
    if not tokens:
        log.warning(
            "⚠️ Aucun token sélectionné dans %s. Aucun trade simulé.",
            SELECTED_TOKENS_FILE,
        )
        SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
        save_json_file(str(SIMULATION_FILE), [])
        log.info("✅ 0 trade simulé sauvegardé dans %s", SIMULATION_FILE)
        return []

    log.info("🔍 Tokens sélectionnés : %s", tokens)

    # 2) Calcul de la taille notionnelle par position
    per_trade_notional = compute_position_size(
        equity_eur=equity,
        regime=regime,
        risk_mode=risk_mode,
        limits=limits,
    )

    # 3) Simulation extrêmement simple (un BUY simulé par token)
    trades: List[Dict[str, Any]] = []
    SIMULATION_DIR.mkdir(parents=True, exist_ok=True)

    for token in tokens:
        try:
            exchange = get_exchange_for_token(token)
            log.info("💰 Simulation trade pour %s sur %s", token, exchange)

            trade = {
                "token": token,
                "exchange": exchange,
                "timestamp": now_utc_iso(),
                # On utilise "amount" comme notionnel EUR pour la préprod
                "amount": per_trade_notional,
                "notional_eur": per_trade_notional,
                "action": "buy",
                "status": "simulated",
                # contexte de risk pour debug / UI éventuelle
                "regime": regime,
                "risk_mode": risk_mode,
            }
            trades.append(trade)

        except Exception as e:
            log.error(
                "❌ Erreur lors de la simulation du token %s : %s",
                token,
                e,
                exc_info=True,
            )

    # 4) Sauvegarde
    save_json_file(str(SIMULATION_FILE), trades)
    log.info("✅ %d trades simulés sauvegardés dans %s", len(trades), SIMULATION_FILE)

    return trades


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        result = simulate_trades()
        print(
            {
                "server_ts": now_utc_iso(),
                "simulated_count": len(result),
                "output_file": str(SIMULATION_FILE),
            }
        )
    except Exception as e:
        log.exception("❌ Erreur fatale dans generate_trade_simulation : %s", e)
        print({"error": str(e)})
