from pathlib import Path
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file

logger = get_logger("exchange_router")

def _hard_gate() -> tuple[bool, str]:
    """
    Défense en profondeur:
    - kill_switch hard_block
    - governance hard_block (source-of-truth)
    - execution_plan blocked
    Fail-safe: si lecture impossible => block
    """
    try:
        data_dir = get_data_dir()
        dd = Path(data_dir)

        ks   = load_json_file(dd / "trading" / "kill_switch.json", default={})
        gov  = load_json_file(dd / "analysis" / "governance_engine_pro.json", default={})
        plan = load_json_file(dd / "trading" / "execution_plan.json", default={})

        if isinstance(ks, dict) and bool(ks.get("hard_block")):
            return False, "kill_switch_hard_block"

        if isinstance(gov, dict) and bool(gov.get("hard_block")):
            return False, "governance_hard_block"

        if isinstance(plan, dict):
            st = str(plan.get("status") or "").lower()
            if st == "blocked":
                return False, "execution_plan_blocked"

        return True, "ok"
    except Exception as e:
        logger.exception("[exchange_router] HARD GATE exception => block: %s", e)
        return False, f"hard_gate_exception:{type(e).__name__}:{e}"

def _binance_funcs():
    """
    Lazy import binance_api.
    Retourne (get_price, place_order, token_available) ou (None,None,None) si indisponible.
    """
    try:
        from src.v2.integrations import binance_api as b
        get_price = getattr(b, "get_price", None)
        place_order = getattr(b, "place_order", None)
        token_available = getattr(b, "token_available", None)
        return get_price, place_order, token_available
    except Exception as e:
        logger.warning("[exchange_router] Binance import failed: %s", e)
        return None, None, None

def _mexc_funcs():
    """
    Lazy import mexc_api.
    """
    try:
        from src.v2.integrations import mexc_api as m
        get_price = getattr(m, "get_price", None)
        place_order = getattr(m, "place_order", None)
        token_available = getattr(m, "token_available", None)
        return get_price, place_order, token_available
    except Exception as e:
        logger.warning("[exchange_router] MEXC import failed: %s", e)
        return None, None, None

def get_price(token_symbol: str):
    """Retourne le prix via la plateforme disponible. Fail-safe => None.
    Stratégie:
      - Si token_available() existe, on l'utilise.
      - Sinon, on tente get_price() directement (public endpoints) => meilleur fallback.
    """
    # Binance first
    b_get, _, b_has = _binance_funcs()
    if callable(b_get):
        try:
            if (callable(b_has) and b_has(token_symbol)) or (not callable(b_has)):
                logger.info("Routage prix vers Binance pour %s", token_symbol)
                px = b_get(token_symbol)
                if px is not None:
                    return px
        except Exception as e:
            logger.warning("Binance get_price failed for %s: %s", token_symbol, e)

    # MEXC fallback
    m_get, _, m_has = _mexc_funcs()
    if callable(m_get):
        try:
            if (callable(m_has) and m_has(token_symbol)) or (not callable(m_has)):
                logger.info("Routage prix vers MEXC pour %s", token_symbol)
                px = m_get(token_symbol)
                if px is not None:
                    return px
        except Exception as e:
            logger.warning("MEXC get_price failed for %s: %s", token_symbol, e)

    logger.warning("Prix indisponible pour %s (Binance/MEXC).", token_symbol)
    return None


def place_order(token_symbol: str, amount: float, side: str = "buy"):
    """
    Place un ordre via la plateforme dispo.
    PREPROD-safe: hard gate en amont.
    Fail-safe: si API non dispo => blocked.
    """
    ok, reason = _hard_gate()
    if not ok:
        return {"status": "blocked", "reason": reason}

    b_get, b_place, b_has = _binance_funcs()
    if callable(b_has) and b_has(token_symbol) and callable(b_place):
        logger.info("Placement ordre sur Binance - %s %s %s", side.upper(), amount, token_symbol)
        return b_place(token_symbol, amount, side)

    m_get, m_place, m_has = _mexc_funcs()
    if callable(m_has) and m_has(token_symbol) and callable(m_place):
        logger.info("Placement ordre sur MEXC - %s %s %s", side.upper(), amount, token_symbol)
        return m_place(token_symbol, amount, side)

    return {"status": "blocked", "reason": "router_dependency_missing_or_token_unavailable"}
