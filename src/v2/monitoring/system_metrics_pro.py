from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file
from src.v2.core.message_bus import publish_event
from src.v2.utils.logger import get_logger  # ✅ logger centralisé

logger = get_logger("system_metrics_pro")


def utc_now_iso() -> str:
    """Retourne un timestamp UTC ISO8601 (secondes, suffixe Z)."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _safe_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}


def build_system_metrics() -> Dict[str, Any]:
    """
    Agrège toutes les métriques clés du système NSC :
    - orchestrator
    - risk limits / kill-switch
    - risk engine PRO
    - governance engine PRO
    - backpressure engine PRO
    - stress test engine
    - execution engine PRO
    - portfolio engine PRO
    - weak signals + meta-score
    """

    data_dir: Path = get_data_dir()
    telemetry_dir = data_dir / "telemetry"
    analysis_dir = data_dir / "analysis"
    trading_dir = data_dir / "trading"

    # --- Lecture des différentes sources (robuste, avec defaults) ---
    orchestrator = _safe_dict(
        load_json_file(telemetry_dir / "orchestrator_pro.json", default={})
    )
    backpressure = _safe_dict(
        load_json_file(telemetry_dir / "backpressure_state.json", default={})
    )
    production_protocol = _safe_dict(
        load_json_file(telemetry_dir / "production_protocol.json", default={})
    )

    risk_limits = _safe_dict(
        load_json_file(trading_dir / "risk_limits.json", default={})
    )
    kill_switch = _safe_dict(
        load_json_file(trading_dir / "kill_switch.json", default={})
    )

    risk_engine = _safe_dict(
        load_json_file(analysis_dir / "risk_engine_pro.json", default={})
    )
    governance = _safe_dict(
        load_json_file(analysis_dir / "governance_engine_pro.json", default={})
    )
    stress_test = _safe_dict(
        load_json_file(analysis_dir / "stress_test_engine.json", default={})
    )
    execution = _safe_dict(
        load_json_file(analysis_dir / "execution_engine_pro.json", default={})
    )
    portfolio = _safe_dict(
        load_json_file(analysis_dir / "portfolio_engine_pro.json", default={})
    )
    weak_signals = _safe_dict(
        load_json_file(analysis_dir / "weak_signals_engine_pro.json", default={})
    )
    meta_score = _safe_dict(
        load_json_file(analysis_dir / "meta_score_pro.json", default={})
    )

    env = os.getenv("NSC_ENV", orchestrator.get("env") or "PREPROD")

    # --- Extraction des sous-structures utiles ---
    risk_stats = _safe_dict(risk_engine.get("stats"))
    stress_summary = _safe_dict(
        stress_test.get("summary") or stress_test.get("summary", {})
    )
    exec_stats = _safe_dict(execution.get("stats"))
    portfolio_stats = _safe_dict(portfolio.get("stats"))
    portfolio_constraints = _safe_dict(portfolio.get("constraints"))

    weak_stats = _safe_dict(
        weak_signals.get("stats") or weak_signals.get("summary", {})
    )

    meta_stats = {
        "global_flag": meta_score.get("global_flag"),
        "avg_meta_score": meta_score.get("avg_meta_score"),
    }

    # --- Synthèse haute niveau ---
    summary: Dict[str, Any] = {
        "mode": orchestrator.get("mode"),
        "can_trade": orchestrator.get("can_trade"),

        "risk_mode": orchestrator.get("risk_mode") or risk_limits.get("risk_mode"),
        "risk_on_off": orchestrator.get("risk_on_off") or risk_limits.get("risk_on_off"),

        "governance_flag": orchestrator.get("governance_flag") or governance.get("flag"),
        "governance_score": orchestrator.get("governance_score") or governance.get("score"),

        "backpressure_mode": orchestrator.get("backpressure_mode")
        or backpressure.get("mode"),
        "production_mode": orchestrator.get("production_mode")
        or production_protocol.get("mode"),

        "kill_switch_mode": kill_switch.get("mode"),
        "kill_switch_enabled": kill_switch.get("enabled"),

        "stress_flag": stress_summary.get("global_flag"),
        "stress_nb_breaches": stress_summary.get("nb_breaches"),
        "worst_drawdown_pct": stress_summary.get("worst_drawdown_pct"),

        "risk_global_flag": risk_stats.get("global_flag"),
        "weak_signals_flag": weak_stats.get("global_flag"),
        "meta_score_flag": meta_stats.get("global_flag"),

        "execution_flag": exec_stats.get("global_flag"),
        "portfolio_constraints_status": portfolio_constraints.get("status"),

        "nb_signals": exec_stats.get("nb_signals"),
        "nb_positions": portfolio_stats.get("nb_positions"),
    }

    # --- Calcul d'un flag global système ---
    system_flag = "ok"
    system_reasons = []

    # Conditions critiques
    if summary.get("stress_flag") == "critical":
        system_flag = "critical"
        system_reasons.append("stress_test.global_flag=critical")

    if summary.get("governance_flag") == "hard_block":
        system_flag = "critical"
        system_reasons.append("governance.flag=hard_block")

    if summary.get("risk_on_off") == "off":
        system_flag = "critical"
        system_reasons.append("risk_on_off=off")

    if kill_switch.get("hard_block"):
        system_flag = "critical"
        system_reasons.append("kill_switch.hard_block=True")

    # Conditions de warning (si pas déjà critical)
    warning_flags = [
        summary.get("risk_global_flag"),
        summary.get("weak_signals_flag"),
        summary.get("meta_score_flag"),
        summary.get("execution_flag"),
    ]
    if system_flag != "critical" and any(
        f in ("caution", "warning") for f in warning_flags if f is not None
    ):
        system_flag = "warning"
        system_reasons.append("sub_engines in caution/warning")

    # Si orchestrator en degraded/emergency mais pas critical ailleurs
    if system_flag == "ok" and summary.get("mode") in ("degraded", "emergency"):
        system_flag = "warning"
        system_reasons.append(f"orchestrator.mode={summary.get('mode')}")

    summary["system_flag"] = system_flag
    summary["system_flag_reasons"] = system_reasons

    # --- Payload complet ---
    payload: Dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "env": env,
        "summary": summary,
        "orchestrator": orchestrator,
        "risk_limits": risk_limits,
        "kill_switch": kill_switch,
        "risk_engine": risk_stats,
        "governance": {
            "flag": governance.get("flag"),
            "score": governance.get("score"),
            "can_trade_recommended": governance.get("can_trade_recommended"),
        },
        "backpressure": backpressure,
        "stress_test": {
            "global_flag": stress_summary.get("global_flag"),
            "nb_breaches": stress_summary.get("nb_breaches"),
            "worst_drawdown_pct": stress_summary.get("worst_drawdown_pct"),
        },
        "execution": exec_stats,
        "portfolio": {
            "stats": portfolio_stats,
            "constraints": portfolio_constraints,
        },
        "weak_signals": weak_stats,
        "meta_score": meta_stats,
    }

    return payload


def main() -> None:
    data_dir: Path = get_data_dir()
    telemetry_dir = data_dir / "telemetry"
    telemetry_path = telemetry_dir / "system_metrics_pro.json"

    metrics = build_system_metrics()
    save_json_file(telemetry_path, metrics)

    summary = metrics.get("summary", {}) or {}
    system_flag = summary.get("system_flag")
    can_trade = summary.get("can_trade")

    logger.info(
        "[system_metrics_pro] system_metrics_pro.json sauvegardé "
        "(system_flag=%s, can_trade=%s)",
        system_flag,
        can_trade,
    )

    # Publication dans l'Event Bus
    severity = "info"
    if system_flag == "warning":
        severity = "warning"
    elif system_flag == "critical":
        severity = "critical"

    try:
        publish_event(
            "metrics.snap",
            "system_metrics_pro",
            {
                "timestamp": metrics.get("timestamp"),
                "env": metrics.get("env"),
                "system_flag": system_flag,
                "can_trade": can_trade,
                "mode": summary.get("mode"),
                "risk_on_off": summary.get("risk_on_off"),
                "governance_flag": summary.get("governance_flag"),
                "backpressure_mode": summary.get("backpressure_mode"),
                "production_mode": summary.get("production_mode"),
                "stress_flag": summary.get("stress_flag"),
                "risk_flag": summary.get("risk_global_flag"),
                "weak_signals_flag": summary.get("weak_signals_flag"),
                "meta_score_flag": summary.get("meta_score_flag"),
                "execution_flag": summary.get("execution_flag"),
                "portfolio_constraints_status": summary.get(
                    "portfolio_constraints_status"
                ),
                "reasons": summary.get("system_flag_reasons", []),
            },
            severity=severity,
        )
        logger.info(
            "[system_metrics_pro] Event metrics.snap publié (severity=%s)", severity
        )
    except Exception as e:  # robustesse
        logger.exception(
            "[system_metrics_pro] Impossible de publier l'event metrics.snap : %s", e
        )


if __name__ == "__main__":
    main()
