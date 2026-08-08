from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def should_close_position_v2(
    position: Dict[str, Any],
    lifecycle_config: Dict[str, Any] | None = None,
) -> Tuple[bool, str]:
    """
    Décide si une position doit être fermée.
    Règles V2 :
    - take profit
    - stop loss
    - fermeture avant expiration
    """
    lifecycle_config = lifecycle_config or {}

    pnl_pct = safe_float(position.get("pnl_pct", 0.0), 0.0)
    days_to_expiry = int(position.get("days_to_expiry", 0))

    take_profit_pct = safe_float(
        position.get("take_profit_pct", lifecycle_config.get("default_take_profit_pct", 50.0)),
        safe_float(lifecycle_config.get("default_take_profit_pct", 50.0), 50.0),
    )
    stop_loss_pct = safe_float(
        position.get("stop_loss_pct", lifecycle_config.get("default_stop_loss_pct", -50.0)),
        safe_float(lifecycle_config.get("default_stop_loss_pct", -50.0), -50.0),
    )
    force_close_days = int(lifecycle_config.get("force_close_days_to_expiry", 5))

    if pnl_pct >= take_profit_pct:
        return True, "take_profit"

    if pnl_pct <= stop_loss_pct:
        return True, "stop_loss"

    if days_to_expiry <= force_close_days:
        return True, "close_before_expiry"

    return False, ""


def close_position_v2(
    position: Dict[str, Any],
    reason: str,
    mode: str = "SIMULATION",
) -> Dict[str, Any]:
    """
    Ferme une position et retourne l'événement trade associé.
    """
    position["status"] = "CLOSED"
    position["ts_close"] = utc_now_iso()
    position["close_reason"] = reason

    trade_event = {
        "ts": utc_now_iso(),
        "action": "CLOSE",
        "ticker": position.get("ticker"),
        "strategy": position.get("strategy"),
        "pnl_eur": safe_float(position.get("pnl_eur", 0.0), 0.0),
        "pnl_pct": safe_float(position.get("pnl_pct", 0.0), 0.0),
        "reason": reason,
        "mode": mode,
    }

    return trade_event
