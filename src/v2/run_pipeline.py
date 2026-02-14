"""
NSC shim: v2.run_pipeline

Point d’entrée stable pour `python -m v2.run_pipeline`.
Il orchestre les étapes minimales (regime -> allocation -> reporting),
tout en restant tolérant aux modules manquants (log + skip).
"""

from __future__ import annotations
import json
import logging
import inspect
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
    """Importe puis appelle prudemment une fonction si elle existe, sinon log un skip.
    Adapte automatiquement les args à la signature (0 arg vs 1 arg, etc.)."""
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
        sig = inspect.signature(fn)
        # si la fonction accepte *args/**kwargs => on passe tout
        if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in sig.parameters.values()):
            return fn(*args, **kwargs)

        # sinon on ne passe que ce qu'elle peut prendre
        params = list(sig.parameters.values())
        max_pos = sum(1 for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty)

        # Cas simple: si elle n'attend rien => call sans args
        if len(sig.parameters) == 0:
            return fn()

        # Si elle attend 1 param obligatoire et qu'on en a un => ok
        if max_pos >= 1 and len(args) >= 1:
            return fn(args[0])

        # Sinon on tente sans args
        return fn()
    except Exception as e:
        log.exception("erreur à l'exécution de %s.%s: %s", mod_name, func_name, e)
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
    regime = _try_call("src.v2.analysis.market_regime_detector","main") \
             or {"regime": "unknown"}
    log.info("regime=%s", regime)

    # 2) Allocation dynamique (si présent)
    alloc = _try_call("src.v2.portfolio.capital_allocator","main", regime) \
            or {"status": "no_profit", "splits": {}}
    log.info("allocation=%s", alloc)

    # 3) Risk controller (si présent)
    _try_call("src.v2.monitoring.risk_controller","main", alloc)

    # 4) Rapport quotidien (si présent)
    rep_path = _try_call("src.v2.reporting.generate_daily_report", "generate_daily_report", alloc) \
               or None
    if rep_path:
        log.info("daily_report: %s", rep_path)

    # 5) Worst trade analyzer (si présent)
    _try_call("src.v2.analysis.worst_trade_analyzer", "analyze_and_notify")

    print(json.dumps({"ts": _iso_now(), "scope": "run_pipeline", "event": "done"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
