"""
NSC PREPROD pipeline entrypoint (simulated-only).

- Runs with NO required CLI args (systemd friendly).
- Optional legacy mode: --snapshot <path> [--out <path>]
- Best-effort orchestration: log + skip on missing modules/functions.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("nsc.pipeline")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _try_import(mod_name: str):
    try:
        return __import__(mod_name, fromlist=["*"])
    except Exception as e:
        log.warning("module introuvable: %s (%s) — skip", mod_name, e)
        return None

def _try_call(mod_name: str, func_name: str, *args, **kwargs):
    """Importe puis appelle prudemment une fonction si elle existe, sinon log un skip."""
    mod = _try_import(mod_name)
    if mod is None:
        return None
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        log.warning("fonction introuvable: %s.%s — skip", mod_name, func_name)
        return None
    try:
        return fn(*args, **kwargs)
    except TypeError as e:
        # fallback: some funcs accept no positional args
        if args:
            try:
                return fn()
            except Exception:
                log.exception("erreur à l'exécution de %s.%s (fallback): %s", mod_name, func_name, e)
                return None
        log.exception("erreur à l'exécution de %s.%s: %s", mod_name, func_name, e)
        return None
    except Exception as e:
        log.exception("erreur à l'exécution de %s.%s: %s", mod_name, func_name, e)
        return None

def _run_preprod() -> int:
    print(json.dumps({
        "ts": _iso_now(),
        "scope": "run_pipeline",
        "event": "start",
        "mode": "PREPROD",
        "env": ":".join(sys.path[:3]),
    }, ensure_ascii=False))

    # 1) Détection de régime
    regime = _try_call("src.v2.analysis.market_regime_detector", "detect_market_regime") or {"regime": "unknown"}
    log.info("regime=%s", regime)

    # 2) Allocation dynamique
    alloc = _try_call("src.v2.portfolio.capital_allocator", "run", regime)
    if alloc is None:
        alloc = _try_call("src.v2.portfolio.capital_allocator", "run")
    alloc = alloc or {"status": "no_profit", "splits": {}}
    log.info("allocation=%s", alloc)

    # 3) Risk controller
    _try_call("src.v2.monitoring.risk_controller", "main")

    # 4) Rapport quotidien (best-effort, 1 seul appel effectif)
    _try_call("src.v2.analysis.sentiment_scorer_offline", "run")
    _try_call("src.v2.analysis.sentiment_aggregator", "run")
    _try_call("src.v2.analysis.sentiment_trend", "run")

    rep = _try_call("src.v2.reporting.generate_daily_report", "generate_daily_report", alloc)
    if rep is None:
        rep = _try_call("src.v2.reporting.generate_daily_report", "generate_daily_report")
    if rep:
        log.info("daily_report=%s", rep)

    # 5) Worst trades (utiliser la version analytics si dispo; éviter les imports LLM)
    _try_call("src.v2.analysis.worst_trade_analyzer", "analyze_and_notify")

    print(json.dumps({"ts": _iso_now(), "scope": "run_pipeline", "event": "done"}, ensure_ascii=False))
    return 0

def _run_snapshot(snapshot: str, out: str | None) -> int:
    # Mode legacy si tu veux l’utiliser manuellement
    ctx = {"ts": _iso_now(), "scope": "run_pipeline", "event": "start", "mode": "SNAPSHOT", "snapshot": snapshot, "out": out}
    print(json.dumps(ctx, ensure_ascii=False))
    # Ici on ne force rien: tu pourras brancher plus tard un traitement snapshot si besoin.
    print(json.dumps({"ts": _iso_now(), "scope": "run_pipeline", "event": "done"}, ensure_ascii=False))
    return 0

def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])

    # Si appelé sans args (systemd), on exécute directement PREPROD.
    if not argv:
        return _run_preprod()

    # Sinon, on accepte un mode snapshot facultatif (mais pas requis).
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--snapshot", default=None)
    parser.add_argument("--out", default=None)
    ns = parser.parse_args(argv)

    if ns.snapshot:
        return _run_snapshot(ns.snapshot, ns.out)

    # Pas de snapshot => PREPROD quand même
    return _run_preprod()

if __name__ == "__main__":
    raise SystemExit(main())
