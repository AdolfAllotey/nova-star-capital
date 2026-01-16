# src/v2/trading/daily_trading_loop.py

from __future__ import annotations

import os
import time
import inspect
import asyncio
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Dict, List, Optional

from src.v2.utils.file_utils import save_json_file, ensure_dir, load_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("daily_trading_loop")


def _now_utc_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _get_env() -> str:
    return os.environ.get("NSC_ENV", "PREPROD")


def _get_data_dir() -> str:
    root = os.environ.get("NSC_ROOT_DIR") or os.getcwd()
    return os.environ.get("NSC_DATA_DIR", os.path.join(root, "data"))


def _safe_call(func, *args, **kwargs):
    """Appelle une fonction sync ou async de façon unifiée."""
    if inspect.iscoroutinefunction(func):
        return func(*args, **kwargs)
    res = func(*args, **kwargs)
    if inspect.isawaitable(res):
        return res
    return None


async def _run_callable(module_path: str, func_name: str) -> None:
    """
    Import + exécution d'une fonction (sync/async) si elle existe.
    Lève AttributeError si la fonction n'existe pas.
    """
    module = import_module(module_path)
    func = getattr(module, func_name, None)
    if func is None:
        raise AttributeError(f"Fonction {func_name} introuvable dans {module_path}")

    awaitable = _safe_call(func)
    if inspect.isawaitable(awaitable):
        await awaitable


async def _run_step_async(step: Dict[str, Any]) -> Dict[str, Any]:
    start = time.perf_counter()

    index = step.get("index")
    name = step.get("name")
    module_path = step.get("module")
    func_name = step.get("func", "main")

    status = "pending"
    error_msg: Optional[str] = None

    try:
        logger.info("[daily_trading_loop] Démarrage étape %s (%s)", index, name)
        await _run_callable(module_path, func_name)
        status = "ok"
        logger.info("[daily_trading_loop] Étape %s (%s) OK", index, name)

    except AttributeError as e:
        status = "skipped"
        error_msg = str(e)
        logger.warning(
            "[daily_trading_loop] Étape %s (%s) SKIPPED : %s",
            index,
            name,
            error_msg,
        )

    except Exception as e:
        status = "error"
        error_msg = f"{e.__class__.__name__}: {e}"
        logger.exception(
            "[daily_trading_loop] Étape %s (%s) ERROR : %s",
            index,
            name,
            error_msg,
        )

    duration = time.perf_counter() - start
    return {
        "index": index,
        "name": name,
        "module": module_path,
        "func": func_name,
        "status": status,
        "duration_s": round(duration, 3),
        "error": error_msg,
    }


def _build_steps() -> List[Dict[str, Any]]:
    """
    Pipeline PREPROD “tout raccordé” :
    1) scrapers -> social_feed
    2) sentiment
    3) engines core (regime/conditions/quality/meta-score)
    4) orchestrator
    5) trading kernel (main ou run_once fallback)
    6) knowledge daily
    7) post steps (snapshot/export/portfolio/governance/etc.)
    """

    steps: List[Dict[str, Any]] = []

    # --- DATA INGEST ---
    steps += [
        {"name": "scrapers", "module": "src.v2.monitoring.run_scrapers", "func": "main_async"},
        {"name": "sentiment_analyzer", "module": "src.v2.analysis.sentiment_analyzer", "func": "analyze_sentiment"},
    ]

    # --- ANALYSIS ENGINES (core) ---
    steps += [
        {"name": "market_regime_detector", "module": "src.v2.analysis.market_regime_detector", "func": "main"},
        {"name": "market_conditions_engine_pro", "module": "src.v2.analysis.market_conditions_engine_pro", "func": "main"},

        # --- MACRO / CROSS-ASSET ---
        {"name": "nasdaq_regime_engine", "module": "src.v2.analysis.nasdaq_regime_engine", "func": "main"},
        {"name": "dollar_regime_engine", "module": "src.v2.analysis.dollar_regime_engine", "func": "main"},

        {"name": "signal_quality_engine_pro", "module": "src.v2.analysis.signal_quality_engine_pro", "func": "main"},
        {"name": "meta_score_engine_pro", "module": "src.v2.analysis.meta_score_engine_pro", "func": "main"},
    ]

    steps += [
        {"name": "risk_controller", "module": "src.v2.monitoring.risk_controller", "func": "main"},
    ]

    # --- ORCHESTRATION ---
    steps += [
        {"name": "orchestrator_pro", "module": "src.v2.monitoring.orchestrator_pro", "func": "main"},
    ]

    # --- TRADING ---
    # NOTE: on ne met PAS run_once ici en step séparée → on le gère proprement dans main_async()
    steps += [
        {"name": "trading_kernel", "module": "src.v2.trading.trading_kernel", "func": "main"},
    ]

    # --- INTELLIGENCE (KNOWLEDGE ENGINE) ---
    steps += [
        {"name": "knowledge_daily_generator", "module": "src.v2.intelligence.knowledge_daily_generator", "func": "main"},
    ]

    # --- POST / REPORTING / OPERATIONS ---
    steps += [
        {"name": "market_snapshot_exporter", "module": "src.v2.analysis.market_snapshot_exporter", "func": "main"},        {"name": "portfolio_engine_pro", "module": "src.v2.analysis.portfolio_engine_pro", "func": "main"},
        {"name": "governance_engine_pro", "module": "src.v2.analysis.governance_engine_pro", "func": "main"},
        {"name": "signal_dispatcher_telegram", "module": "src.v2.trading.signal_dispatcher_telegram", "func": "main"},
        {"name": "backpressure_engine_pro", "module": "src.v2.monitoring.backpressure_engine_pro", "func": "main"},
        {"name": "cost_tracker", "module": "src.v2.monitoring.cost_tracker", "func": "main"},
        {"name": "profitability_tracker", "module": "src.v2.monitoring.profitability_tracker", "func": "main"},
    ]

    # index auto
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(steps, start=1):
        out.append({"index": i, **s})
    return out


async def _run_trading_kernel_with_fallback() -> Dict[str, Any]:
    """
    Exécute trading_kernel.main() si possible.
    Sinon, fallback sur trading_kernel.run_once().
    Retourne un "step_result" standardisé.
    """
    step_main = {"index": None, "name": "trading_kernel", "module": "src.v2.trading.trading_kernel", "func": "main"}
    res_main = await _run_step_async(step_main)

    if res_main["status"] == "ok":
        return res_main

    # si main est skipped ou error -> on tente run_once
    step_once = {"index": None, "name": "trading_kernel_run_once", "module": "src.v2.trading.trading_kernel", "func": "run_once"}
    res_once = await _run_step_async(step_once)

    # si run_once ok, on considère le trading_kernel comme ok (fallback)
    if res_once["status"] == "ok":
        return {
            **res_once,
            "name": "trading_kernel",
            "func": "run_once",
            "error": None,
        }

    # sinon, on renvoie le résultat le plus informatif
    # (si main error -> garde main, sinon garde run_once)
    if res_main["status"] == "error":
        return res_main
    return res_once


async def main_async() -> None:
    env = _get_env()
    data_dir = _get_data_dir()
    telemetry_dir = os.path.join(data_dir, "telemetry")
    # PREWRITE_TELEMETRY_LOGS_OVERVIEW_LIGHT
    # Écrit un stub dès le début pour éviter le warning backpressure (fichier absent)
    try:
        save_json_file(os.path.join(telemetry_dir, "logs_overview_light.json"), {
            "timestamp": _now_utc_iso(),
            "env": env,
            "has_errors": False,
            "steps_total": 0,
            "steps_ok": 0,
            "steps_error": 0,
            "failed_steps": [],
            "steps": {},
            "note": "prewrite_stub",
        })
    except Exception:
        pass

    analysis_dir = os.path.join(data_dir, "analysis")
    state_dir = os.path.join(data_dir, "state")

    ensure_dir(data_dir)
    ensure_dir(telemetry_dir)
    ensure_dir(analysis_dir)
    ensure_dir(state_dir)

    orchestrator_path = os.path.join(telemetry_dir, "orchestrator_pro.json")
    orchestrator_can_trade = False  # default SAFE
    orchestrator_mode = None
    orchestrator_reasons = []

    logger.info("[daily_trading_loop] Lancement de la boucle journalière (env=%s, data_dir=%s)", env, data_dir)

    steps = _build_steps()

    t0 = time.perf_counter()
    step_results: List[Dict[str, Any]] = []

    for step in steps:
        # --- ORCHESTRATOR GATE ---
        if step["name"] == "orchestrator_pro":
            res = await _run_step_async(step)
            step_results.append(res)

            # Lecture de l'état orchestrator (source of truth)
            try:
                st = load_json_file(orchestrator_path, default={})
                orchestrator_can_trade = bool(st.get("can_trade", False))
                orchestrator_mode = st.get("mode")
                orchestrator_reasons = st.get("reasons") or []
                logger.info(
                    "[daily_trading_loop] orchestrator gate -> can_trade=%s mode=%s reasons=%s",
                    orchestrator_can_trade, orchestrator_mode, orchestrator_reasons
                )
            except Exception as e:
                orchestrator_can_trade = False
                orchestrator_mode = "unknown"
                orchestrator_reasons = [f"orchestrator_state_unreadable: {e}"]
                logger.warning("[daily_trading_loop] orchestrator gate fallback SAFE (can_trade=False): %s", e)

            continue

        # trading_kernel: exécuter seulement si autorisé par orchestrator
        if step["name"] == "trading_kernel":
            if not orchestrator_can_trade:
                step_results.append({
                    "index": step["index"],
                    "name": "trading_kernel",
                    "module": step.get("module"),
                    "func": step.get("func"),
                    "status": "skipped",
                    "error": None,
                    "details": {
                        "reason": "orchestrator_can_trade_false",
                        "orchestrator_mode": orchestrator_mode,
                        "orchestrator_reasons": orchestrator_reasons,
                        "orchestrator_path": orchestrator_path,
                    },
                })
                logger.warning(
                    "[daily_trading_loop] trading_kernel SKIPPED (orchestrator can_trade=False) mode=%s reasons=%s",
                    orchestrator_mode, orchestrator_reasons
                )
                continue

            # trading_kernel: gestion propre du fallback
            res = await _run_trading_kernel_with_fallback()
            res["index"] = step["index"]
            step_results.append(res)
            continue

        res = await _run_step_async(step)
        step_results.append(res)

    total_duration = time.perf_counter() - t0

    steps_total = len(step_results)
    steps_ok = sum(1 for s in step_results if s["status"] == "ok")
    steps_error = sum(1 for s in step_results if s["status"] == "error")
    failed_steps = [s["name"] for s in step_results if s["status"] == "error"]

    system_metrics = {
        "timestamp": _now_utc_iso(),
        "env": env,
        "duration_s": round(total_duration, 3),
        "steps_total": steps_total,
        "steps_ok": steps_ok,
        "steps_error": steps_error,
        "failed_steps": failed_steps,
    }
    save_json_file(os.path.join(telemetry_dir, "system_metrics.json"), system_metrics)

    logs_overview = {
        "timestamp": _now_utc_iso(),
        "env": env,
        "has_errors": steps_error > 0,
        "steps_total": steps_total,
        "steps_ok": steps_ok,
        "steps_error": steps_error,
        "failed_steps": failed_steps,
        "steps": step_results,
    }
    save_json_file(os.path.join(analysis_dir, "logs_overview_light.json"), logs_overview)
    save_json_file(os.path.join(telemetry_dir, "logs_overview_light.json"), logs_overview)

    if steps_error > 0:
        logger.warning(
            "[daily_trading_loop] Boucle terminée AVEC ERREURS (%s/%s étapes en erreur)",
            steps_error,
            steps_total,
        )
    else:
        logger.info(
            "[daily_trading_loop] Boucle terminée SANS ERREUR (%s étapes, durée=%.3fs)",
            steps_total,
            total_duration,
        )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
