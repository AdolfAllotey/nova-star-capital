"""
NSC shim: v2.run_pipeline

Point d’entrée stable pour `python -m v2.run_pipeline`.
Il orchestre les étapes minimales (regime -> allocation -> reporting),
tout en restant tolérant aux modules manquants (log + skip).
"""

from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timezone

log = logging.getLogger("nsc.pipeline")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _try_call(mod_name: str, func_name: str, *args, **kwargs):
    """Importe puis appelle prudemment une fonction si elle existe, sinon log un skip."""
    try:
        mod = __import__(mod_name, fromlist=[func_name])
    except Exception as e:
        log.warning("module introuvable: %s (%s) — skip", mod_name, e)
        return None
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        log.warning("fonction introuvable: %s.%s — skip", mod_name, func_name)
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log.exception("erreur à l'exécution de %s.%s: %s", mod_name, func_name, e)
        return None

def main():
    ctx = {
        "ts": _iso_now(),
        "scope": "run_pipeline",
        "event": "start",
        "version": "v2-shim",
        "env": ":".join(sys.path[:3]),
    }
    print(json.dumps(ctx, ensure_ascii=False))

    # 1) Détection de régime (si présent)
    regime = _try_call("v2.strategy.market_regime_detector", "detect_regime") \
             or {"regime": "unknown"}
    log.info("regime=%s", regime)

    # 2) Allocation dynamique (si présent)
    alloc = _try_call("v2.strategy.capital_allocator", "allocate", regime) \
            or {"status": "no_profit", "splits": {}}
    log.info("allocation=%s", alloc)

    # 3) Risk controller (si présent)
    _try_call("v2.risk.controller", "adjust_positions", alloc)

    # 4) Rapport quotidien (si présent)
    rep_path = _try_call("v2.reporting.daily_report", "generate_daily_report", alloc) \
               or None
    if rep_path:
        log.info("daily_report: %s", rep_path)

    # 5) Worst trade analyzer (si présent)
    _try_call("v2.analysis.worst_trade_analyzer", "analyze_and_notify")

    print(json.dumps({"ts": _iso_now(), "scope": "run_pipeline", "event": "done"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
