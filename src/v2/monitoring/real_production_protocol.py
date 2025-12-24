from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


# ---------- Helpers génériques ----------


def utcnow_iso() -> str:
    """Retourne un timestamp ISO UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_data_dir() -> Path:
    """
    Version simple : on lit NSC_DATA_DIR si présent, sinon 'data/'.
    """
    base = os.getenv("NSC_DATA_DIR", "data")
    return Path(base).resolve()


def get_env() -> str:
    """
    Environnement logique : PREPROD par défaut, PROD en réel.
    """
    return os.getenv("NSC_ENV", "PREPROD")


def _load_json_safe(path: Path, default: Any) -> Any:
    """
    Lecture JSON robuste avec valeur par défaut.
    Évite les dépendances à file_utils.load_json.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("JSON file not found: %s → returning default", path)
        return default
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in %s → %s → returning default", path, exc)
        return default
    except Exception as exc:  # pragma: no cover – robustesse
        logger.warning("Error loading JSON %s → %s → returning default", path, exc)
        return default


def _save_json(path: Path, data: Any) -> None:
    """
    Écriture JSON avec création du dossier parent si besoin.
    Évite les dépendances à file_utils.save_json.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
        logger.info("Saved JSON file: %s", path)
    except Exception as exc:  # pragma: no cover – robustesse
        logger.error("Error saving JSON %s → %s", path, exc)


# ---------- Construction du snapshot Real Production ----------


def build_real_production_snapshot(data_dir: Path, env: str) -> Dict[str, Any]:
    """
    Construit l'état complet du Real Production Protocol.

    On agrège :
    - orchestrator_pro
    - governance_engine_pro
    - system_metrics_pro
    - backpressure_state
    - stress_test_engine
    - kill_switch
    - risk_limits (risk_engine)
    - production_protocol (pré-flight normal)
    """

    telemetry_dir = data_dir / "telemetry"
    analysis_dir = data_dir / "analysis"
    trading_dir = data_dir / "trading"

    orchestrator = _load_json_safe(telemetry_dir / "orchestrator_pro.json", default={})
    governance = _load_json_safe(analysis_dir / "governance_engine_pro.json", default={})
    system_metrics = _load_json_safe(
        telemetry_dir / "system_metrics_pro.json", default={}
    )
    backpressure = _load_json_safe(
        telemetry_dir / "backpressure_state.json", default={}
    )
    stress_test = _load_json_safe(
        analysis_dir / "stress_test_engine.json", default={}
    )
    kill_switch = _load_json_safe(trading_dir / "kill_switch.json", default={})
    risk_limits = _load_json_safe(trading_dir / "risk_limits.json", default={})
    production_proto = _load_json_safe(
        telemetry_dir / "production_protocol.json", default={}
    )

    # Champs clés
    orchestrator_mode = orchestrator.get("mode")
    orchestrator_can_trade = orchestrator.get("can_trade", False)

    governance_flag = (
        governance.get("flag")
        or governance.get("governance_flag")
        or system_metrics.get("governance_flag")
    )
    governance_score = (
        governance.get("score")
        or governance.get("governance_score")
        or system_metrics.get("governance_score")
    )

    risk_mode = (
        risk_limits.get("mode")
        or system_metrics.get("risk_mode")
        or "unknown"
    )
    risk_on_off = (
        risk_limits.get("risk_on_off")
        or system_metrics.get("risk_on_off")
        or "off"
    )

    backpressure_mode = backpressure.get("mode", "unknown")
    production_mode = production_proto.get("mode", "unknown")

    stress_flag = None
    stress_nb_breaches = None
    stress_worst_dd = None
    if stress_test:
        summary = stress_test.get("summary", {})
        stress_flag = summary.get("global_flag")
        stress_nb_breaches = summary.get("nb_breaches")
        stress_worst_dd = summary.get("worst_drawdown_pct")

    kill_status = kill_switch.get("status") or (
        "on" if kill_switch.get("enabled") else "off"
    )
    kill_mode = kill_switch.get("mode", "soft")

    # ---------- Règles de protocole ----------
    stage = "unknown"
    mode = "unknown"
    can_trade = False
    severity = "info"
    reasons: List[str] = []

    # 1) Environnement
    if env != "PROD":
        stage = "shadow"
        mode = "shadow_mode"
        severity = "warning"
        reasons.append(f"env={env} (shadow / préproduction, aucun trade réel autorisé)")

    # 2) Kill switch global
    if kill_status == "on":
        mode = "kill_switch_on"
        severity = "critical"
        reasons.append(
            f"Kill switch global actif (mode={kill_mode}, reason={kill_switch.get('reason')})"
        )

    # 3) Gouvernance
    if governance_flag == "hard_block":
        mode = "governance_hard_block"
        severity = "critical"
        reasons.append(
            "Gouvernance en HARD BLOCK (governance.flag=hard_block, can_trade_recommended=False)"
        )

    # 4) Risk Engine
    if risk_on_off == "off":
        mode = "risk_engine_off"
        severity = "critical"
        reasons.append("Risk Engine en mode OFF (risk_on_off=off, size_factor=0)")

    # 5) Backpressure
    if backpressure_mode in ("degraded", "emergency"):
        severity = "critical"
        reasons.append(
            f"Backpressure en mode {backpressure_mode} (pas de montée en Real Production)"
        )

    # 6) Stress tests
    if stress_flag == "critical" or (
        isinstance(stress_nb_breaches, int) and stress_nb_breaches > 0
    ):
        severity = "critical"
        reasons.append(
            f"Stress Test Engine en état critique (flag={stress_flag}, nb_breaches={stress_nb_breaches})"
        )

    # 7) Orchestrator
    if orchestrator_mode in ("emergency", "degraded") or not orchestrator_can_trade:
        severity = "critical"
        reasons.append(
            f"Orchestrator en mode {orchestrator_mode} (can_trade={orchestrator_can_trade})"
        )

    # Si aucune raison critique et qu'on est en PROD, on ouvre la porte
    if (
        env == "PROD"
        and kill_status != "on"
        and governance_flag != "hard_block"
        and risk_on_off == "on"
        and backpressure_mode == "normal"
        and orchestrator_mode == "normal"
        and orchestrator_can_trade
    ):
        stage = "real_production"
        mode = "normal"
        can_trade = True
        severity = "info"
        if not reasons:
            reasons.append(
                "Toutes les checks critiques sont au vert (Real Production OK)."
            )
    else:
        can_trade = False
        if severity == "info":
            severity = "warning"
        if not reasons:
            reasons.append(
                "Conditions non réunies pour la Real Production (safe default)."
            )

    snapshot: Dict[str, Any] = {
        "timestamp": utcnow_iso(),
        "env": env,
        "stage": stage,
        "mode": mode,
        "can_trade": can_trade,
        "severity": severity,
        "reasons": reasons,
        "checks": {
            "orchestrator": {
                "mode": orchestrator_mode,
                "can_trade": orchestrator_can_trade,
            },
            "governance": {
                "flag": governance_flag,
                "score": governance_score,
            },
            "risk_engine": {
                "mode": risk_mode,
                "risk_on_off": risk_on_off,
            },
            "backpressure": {
                "mode": backpressure_mode,
            },
            "production_protocol": {
                "mode": production_mode,
            },
            "stress_test": {
                "flag": stress_flag,
                "nb_breaches": stress_nb_breaches,
                "worst_drawdown_pct": stress_worst_dd,
            },
            "kill_switch": {
                "status": kill_status,
                "mode": kill_mode,
                "reason": kill_switch.get("reason"),
            },
        },
    }

    return snapshot


# ---------- Entrée principale ----------


def main() -> None:
    env = get_env()
    data_dir = get_data_dir()
    telemetry_dir = (data_dir / "telemetry").resolve()
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[real_production_protocol] DATA_DIR=%s, env=%s", data_dir, env)

    snapshot = build_real_production_snapshot(data_dir=data_dir, env=env)

    out_path = telemetry_dir / "real_production_protocol.json"
    _save_json(out_path, snapshot)
    logger.info(
        "[real_production_protocol] real_production_protocol.json sauvegardé "
        "(stage=%s, mode=%s, can_trade=%s, severity=%s)",
        snapshot["stage"],
        snapshot["mode"],
        snapshot["can_trade"],
        snapshot["severity"],
    )

    # Publication sur le bus d’événements
    try:
        publish_event(
            "real_production.state",
            "real_production_protocol",
            snapshot,
            severity=snapshot.get("severity", "info"),
        )
        logger.info(
            "[real_production_protocol] Event real_production.state publié (severity=%s)",
            snapshot.get("severity", "info"),
        )
    except Exception as exc:  # pragma: no cover – robustesse
        logger.warning(
            "[real_production_protocol] Impossible de publier l'événement "
            "real_production.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
