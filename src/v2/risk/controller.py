# /opt/nsc/app/src/v2/risk/controller.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

log = logging.getLogger("nsc.risk.controller")
log.setLevel(logging.INFO)


def adjust_positions(
    allocation_result: Dict[str, Any],
    max_dd_threshold: float = -0.25,   # si drawdown global < -25% => risk_off
    max_leverage: float = 1.0,         # cap levier
    dry_run: bool = False,
    telemetry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Décide d’un “sizing” de risque global et de l’action à appliquer.
    Entrée minimale : allocation_result (avec 'regime' et 'confidence').
    """
    regime = allocation_result.get("regime", "neutral")
    conf = float(allocation_result.get("confidence", 0.5))
    drivers = (telemetry or {}).get("drivers", {})
    dd = float(drivers.get("drawdown", 0.0))  # drawdown global éventuel

    action = "noop"
    reason = "steady_state"
    risk_multiplier = 1.0

    if dd <= max_dd_threshold:
        action = "risk_off"
        reason = f"global drawdown {dd:.2%} <= {max_dd_threshold:.0%}"
        risk_multiplier = 0.0
    else:
        if regime == "bear":
            action = "reduce"
            reason = "bear regime"
            risk_multiplier = 0.5 if conf >= 0.6 else 0.7
        elif regime == "bull":
            action = "increase"
            reason = "bull regime"
            risk_multiplier = 1.0 if conf < 0.6 else 1.2
        else:
            action = "noop"
            reason = "neutral regime"
            risk_multiplier = 0.9 if conf < 0.5 else 1.0

    # clamp global
    risk_multiplier = max(0.0, min(max_leverage, risk_multiplier))

    result = {
        "action": action,
        "reason": reason,
        "risk_multiplier": round(risk_multiplier, 3),
        "input_status": allocation_result.get("status", "ok"),
        "regime": regime,
        "confidence": round(conf, 3),
        "dry_run": dry_run,
    }
    log.info("risk.controller.adjust_positions -> %s", result)
    return result
