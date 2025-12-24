# /opt/nsc/app/src/v2/strategy/market_regime_detector.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("nsc.strategy.regime")
log.setLevel(logging.INFO)

# Emplacement optionnel d’un état marché “local” pour surcharger
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "runtime" / "market_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class RegimeConfig:
    bear_dd_threshold: float = -0.20   # drawdown <= -20% => bear
    bull_momentum_threshold: float = 0.10  # momentum >= +10% => bull
    neutral_confidence: float = 0.50
    min_confidence: float = 0.30
    max_confidence: float = 0.90


CFG = RegimeConfig()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load_state() -> Dict[str, Any]:
    """Optionnel : permet d’injecter un état marché via fichier (ex: par un job de data)."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception as e:
        log.warning("market_state load failed: %s", e)
    return {}


def detect_regime(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Détection simple : si drawdown <= -20% => BEAR
                        elif momentum >= +10% => BULL
                        else => NEUTRAL
    Priorité des sources: context > fichier local > défaut.
    """
    ctx = dict(_safe_load_state())
    if context:
        ctx.update(context)

    dd = float(ctx.get("drawdown", 0.0))          # ex: -0.18 pour -18%
    mom = float(ctx.get("momentum_30d", 0.0))     # ex: +0.12 pour +12%

    # Règles
    if dd <= CFG.bear_dd_threshold:
        regime = "bear"
        base_conf = min(CFG.max_confidence, max(CFG.min_confidence, 0.70 + min(0.20, abs(dd) - 0.20)))
        reason = f"drawdown {dd:.2%} <= {CFG.bear_dd_threshold:.0%}"
    elif mom >= CFG.bull_momentum_threshold:
        regime = "bull"
        base_conf = min(CFG.max_confidence, max(CFG.min_confidence, 0.65 + min(0.20, mom - 0.10)))
        reason = f"momentum {mom:.2%} >= {CFG.bull_momentum_threshold:.0%}"
    else:
        regime = "neutral"
        base_conf = CFG.neutral_confidence
        reason = "no strong signal (momentum/drawdown)"

    result = {
        "regime": regime,
        "confidence": round(base_conf, 3),
        "ts": _utcnow_iso(),
        "method": "rules_v1",
        "drivers": {"drawdown": dd, "momentum_30d": mom, "reason": reason},
    }
    log.info("market_regime_detector.detect_regime -> %s", result)
    return result
