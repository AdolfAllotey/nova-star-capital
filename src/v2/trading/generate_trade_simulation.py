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
import random

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.exchange_router import get_exchange_for_token

# ---------------------------------------------------------------------
# MARKET DATA (SPOT PRICES)
# ---------------------------------------------------------------------
SPOT_PRICES_FILE = Path("/opt/nsc/data/preprod/market/crypto_spot_prices.json")

def load_spot_prices() -> Dict[str, float]:
    out: Dict[str, float] = {}

    try:
        log.info("DEBUG_SPOT_PATH => %s exists=%s", SPOT_PRICES_FILE, SPOT_PRICES_FILE.exists())

        if not SPOT_PRICES_FILE.exists():
            return out

        import json
        raw = SPOT_PRICES_FILE.read_text(encoding="utf-8")
        log.info("DEBUG_SPOT_RAW => %s", raw[:500])

        data = json.loads(raw)
        log.info("DEBUG_SPOT_DATA_TYPE => %s", type(data).__name__)

        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    for field in ("price_eur", "eur", "price", "current_price_eur", "current_price", "usd"):
                        if v.get(field) is not None:
                            try:
                                out[str(k).upper().strip()] = float(v.get(field))
                                break
                            except Exception:
                                pass
                else:
                    try:
                        out[str(k).upper().strip()] = float(v)
                    except Exception:
                        pass

        elif isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                token = str(row.get("token") or row.get("symbol") or "").upper().strip()
                if not token:
                    continue
                for field in ("price_eur", "eur", "price", "current_price_eur", "current_price", "usd"):
                    if row.get(field) is not None:
                        try:
                            out[token] = float(row.get(field))
                            break
                        except Exception:
                            pass

        log.info("DEBUG_SPOT_PARSED => %s", out)

    except Exception as e:
        log.error("❌ Impossible de lire crypto_spot_prices.json: %s", e, exc_info=True)

    return out


log = get_logger("generate_trade_simulation")

# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "src/v2/data")).expanduser().resolve()
SIMULATION_DIR = DATA_DIR / "simulation"
SIMULATION_FILE = SIMULATION_DIR / "trade_simulation.json"

SELECTED_TOKENS_FILE = DATA_DIR / "selected_tokens.json"
DYNAMIC_SELECTED_TOKENS_FILE = Path("/opt/nsc/data/preprod/trading/selected_tokens.dynamic.json")
RISK_STATE_FILE = DATA_DIR / "reports" / "risk_state.json"
CAPITAL_ALLOCATION_FILE = Path("/opt/nsc/data/preprod/trading/capital_allocation.json")


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_selected_tokens() -> List[Dict[str, Any]]:
    """
    Priorité à la sélection dynamique issue du sentiment overview.
    Fallback sur selected_tokens.json historique.

    Formats supportés :
      - dynamic: {"items":[{"token":"LINK","score":82}, ...]}
      - legacy list: ["bitcoin", "ethereum", "solana"]
      - legacy dict: {"BTC":"BINANCE", "SOL":"MEXC"}
    """
    dynamic_doc = load_json_file(str(DYNAMIC_SELECTED_TOKENS_FILE), default={})
    items = dynamic_doc.get("items", []) if isinstance(dynamic_doc, dict) else []

    if isinstance(items, list) and items:
        out: List[Dict[str, Any]] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            token = str(row.get("token", "")).strip()
            if not token:
                continue
            out.append({
                "token": token,
                "score": float(row.get("score", 0) or 0),
                "mentions": int(row.get("mentions", 0) or 0),
                "source": row.get("source", "dynamic"),
            })
        if out:
            return out

    doc = load_json_file(str(SELECTED_TOKENS_FILE), default=[])

    out: List[Dict[str, Any]] = []
    if isinstance(doc, list):
        out = [{"token": str(t).strip(), "score": 50.0, "source": "legacy_list"} for t in doc if str(t).strip()]
    elif isinstance(doc, dict):
        out = [{"token": str(k).strip(), "score": 50.0, "source": "legacy_dict"} for k in doc.keys() if str(k).strip()]

    return out


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


def load_capital_allocator_context():
    """
    Lit capital_allocation.json et renvoie :
      - trading_budget
      - capital_per_trade
      - max_positions
    """
    data = load_json_file(str(CAPITAL_ALLOCATION_FILE), default={})

    trading_budget = float(data.get("trading_budget", 0.0) or 0.0)
    capital_per_trade = float(data.get("capital_per_trade", 0.0) or 0.0)
    max_positions = int(
        data.get("max_positions", data.get("max_concurrent_positions", 50)) or 50
    )
    if max_positions <= 0:
        max_positions = 50

    return {
        "trading_budget": trading_budget,
        "capital_per_trade": capital_per_trade,
        "max_positions": max_positions,
    }


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
    selected_items = load_selected_tokens()
    if not selected_items:
        log.warning(
            "⚠️ Aucun token sélectionné dans %s. Aucun trade simulé.",
            SELECTED_TOKENS_FILE,
        )
        SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
        save_json_file(str(SIMULATION_FILE), [])
        log.info("✅ 0 trade simulé sauvegardé dans %s", SIMULATION_FILE)
        return []

    log.info("🔍 Tokens sélectionnés : %s", selected_items)

    # 2) Calcul de la taille notionnelle de référence + contexte allocator
    per_trade_notional = compute_position_size(
        equity_eur=equity,
        regime=regime,
        risk_mode=risk_mode,
        limits=limits,
    )
    allocator_ctx = load_capital_allocator_context()
    allocator_capital_per_trade = float(allocator_ctx.get("capital_per_trade", 0.0) or 0.0)
    allocator_trading_budget = float(allocator_ctx.get("trading_budget", 0.0) or 0.0)

    spot_prices = load_spot_prices()
    log.info("DEBUG_SPOT_PRICES => %s", spot_prices)

    filtered_items: List[Dict[str, Any]] = []
    for item in selected_items:
        token = str(item.get("token", "")).strip()
        score = float(item.get("score", 0) or 0)

        if not token:
            continue
        if score < 30:
            log.info("⏭️ Token ignoré car score trop faible: %s (score=%.2f)", token, score)
            continue

        filtered_items.append(item)

    if not filtered_items:
        save_json_file(str(SIMULATION_FILE), [])
        log.info("✅ Aucun trade simulé après filtrage.")
        return []

    # budget déployable : on respecte l'allocator et le garde-fou risk
    reference_per_trade = allocator_capital_per_trade if allocator_capital_per_trade > 0 else per_trade_notional
    reference_per_trade = min(reference_per_trade, per_trade_notional) if per_trade_notional > 0 else reference_per_trade
    deployable_budget = reference_per_trade * len(filtered_items)

    if allocator_trading_budget > 0:
        deployable_budget = min(deployable_budget, allocator_trading_budget)

    total_score = sum(float(x.get("score", 0) or 0) for x in filtered_items) or 1.0

    trades: List[Dict[str, Any]] = []
    SIMULATION_DIR.mkdir(parents=True, exist_ok=True)

    for item in filtered_items:
        token = str(item.get("token", "")).strip()
        score = float(item.get("score", 0) or 0)

        try:
            exchange = get_exchange_for_token(token)
            weight = score / total_score
            notional = round(deployable_budget * weight, 2)

            log.info(
                "💰 Simulation trade pour %s sur %s (score=%.2f weight=%.4f notional=%.2f€)",
                token, exchange, score, weight, notional
            )

            trade = {
                "token": token,
                "score": score,
                "exchange": exchange,
                "timestamp": now_utc_iso(),
                "amount": notional,
                "notional_eur": notional,
                "action": "buy",
                "status": "simulated",
                "regime": regime,
                "risk_mode": risk_mode,
                "selection_source": item.get("source", "dynamic"),
                "mentions": item.get("mentions"),
                "relative_strength": round(float(item.get("relative_strength", 0) or 0), 4),
                "portfolio_weight_inside_crypto": round(weight, 4),
                "entry_price_eur": round(float(spot_prices.get(token.upper(), 0.0) or 0.0), 8) if float(spot_prices.get(token.upper(), 0.0) or 0.0) > 0 else None,
                "quantity_units": round(notional / float(spot_prices.get(token.upper(), 0.0)), 10) if float(spot_prices.get(token.upper(), 0.0) or 0.0) > 0 else None,
                "pnl_eur": None,
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

    try:
        from src.v2.trading.enrich_crypto_trades_from_spot import TRADE_PATH as _TP  # noqa: F401
        import subprocess
        subprocess.run(
            ["python", "/opt/nsc/app/src/v2/trading/enrich_crypto_trades_from_spot.py"],
            check=False
        )
        log.info("✅ enrich_crypto_trades_from_spot.py exécuté après simulation.")
    except Exception as e:
        log.warning("⚠️ Impossible d'exécuter enrich_crypto_trades_from_spot.py : %s", e)

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
