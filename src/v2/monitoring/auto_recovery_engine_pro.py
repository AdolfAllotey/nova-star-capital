import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)
from src.v2.utils.logger import get_logger
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    """Retourne un timestamp ISO8601 en UTC avec suffixe Z."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    """Accès sécurisé dans un dict imbriqué."""
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _load_telemetry_files(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Charge les principaux fichiers de télémétrie.
    On tolère les fichiers manquants en renvoyant des dict vides.
    """
    telemetry_dir = data_dir / "telemetry"
    analysis_dir = data_dir / "analysis"

    files = {
        "orchestrator": telemetry_dir / "orchestrator_pro.json",
        "governance": analysis_dir / "governance_engine_pro.json",
        "risk_limits": data_dir / "trading" / "risk_limits.json",
        "backpressure": telemetry_dir / "backpressure_state.json",
        "stress_test": analysis_dir / "stress_test_engine.json",
        "system_metrics": telemetry_dir / "system_metrics_pro.json",
        "daily_loop": telemetry_dir / "daily_loop_engine_pro.json",
    }

    results: Dict[str, Dict[str, Any]] = {}
    for key, path in files.items():
        try:
            results[key] = load_json_file(path, default={})
        except Exception as e:
            logger.exception(
                "[auto_recovery] Erreur lors du chargement de %s (%s): %s", key, path, e
            )
            results[key] = {}

    return results


def _compute_service_status(telemetry: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Construit une vue par service (orchestrator, governance, risk, backpressure, stress, metrics, daily_loop).
    """
    services: Dict[str, Dict[str, Any]] = {}

    # Orchestrator
    orch = telemetry.get("orchestrator", {})
    services["orchestrator_pro"] = {
        "mode": orch.get("mode"),
        "can_trade": orch.get("can_trade"),
        "reasons": orch.get("reasons", []),
        "backpressure_mode": orch.get("backpressure_mode"),
        "production_mode": orch.get("production_mode"),
        "stress_summary": orch.get("stress_summary"),
    }

    # Governance
    gov = telemetry.get("governance", {})
    services["governance_engine_pro"] = {
        "flag": gov.get("flag"),
        "score": gov.get("score"),
        "can_trade_recommended": gov.get("can_trade_recommended"),
        "reasons": gov.get("reasons", []),
    }

    # Risk / risk_limits
    rl = telemetry.get("risk_limits", {})
    services["risk_engine_pro"] = {
        "risk_mode": rl.get("risk_mode"),
        "risk_on_off": rl.get("risk_on_off"),
        "risk_on": rl.get("risk_on"),
        "size_factor": rl.get("size_factor"),
        "daily_drawdown_pct": rl.get("daily_drawdown_pct"),
        "risk_console_flag": rl.get("risk_console_flag"),
        "kill_switch": rl.get("kill_switch"),
        "mode": rl.get("mode"),
        "max_positions": rl.get("max_positions"),
    }

    # Backpressure
    bp = telemetry.get("backpressure", {})
    services["backpressure_engine_pro"] = {
        "mode": bp.get("mode"),
        "reasons": bp.get("reasons", []),
        "metrics": bp.get("metrics", {}),
        "logs": bp.get("logs", {}),
    }

    # Stress test
    st = telemetry.get("stress_test", {})
    summary = st.get("summary", {})
    services["stress_test_engine"] = {
        "global_flag": summary.get("global_flag"),
        "nb_breaches": summary.get("nb_breaches"),
        "worst_drawdown_pct": summary.get("worst_drawdown_pct"),
    }

    # System metrics
    sm = telemetry.get("system_metrics", {})
    summary_sm = sm.get("summary", {})
    services["system_metrics_pro"] = summary_sm or sm

    # Daily loop
    dl = telemetry.get("daily_loop", {})
    services["daily_loop_engine_pro"] = {
        "phase": dl.get("phase"),
        "flag": dl.get("flag"),
        "can_trade": dl.get("can_trade"),
        "reasons": dl.get("reasons", []),
        "orchestrator_mode": dl.get("orchestrator_mode"),
    }

    return services


def _evaluate_global_state(services: Dict[str, Dict[str, Any]]) -> Tuple[str, bool, str, List[str]]:
    """
    Calcule:
    - mode global : normal / degraded / emergency
    - can_trade_global : bool
    - system_flag : ok / warning / critical
    - root_causes : liste de raisons
    """
    root_causes: List[str] = []

    orch = services.get("orchestrator_pro", {})
    gov = services.get("governance_engine_pro", {})
    risk = services.get("risk_engine_pro", {})
    bp = services.get("backpressure_engine_pro", {})
    stress = services.get("stress_test_engine", {})
    metrics = services.get("system_metrics_pro", {})

    orch_mode = orch.get("mode")
    orch_can_trade = orch.get("can_trade")

    gov_flag = gov.get("flag")
    gov_can_trade = gov.get("can_trade_recommended")

    risk_mode = risk.get("risk_mode")
    risk_on_off = risk.get("risk_on_off")
    size_factor = risk.get("size_factor")

    bp_mode = bp.get("mode")
    stress_flag = stress.get("global_flag")
    system_flag_metrics = metrics.get("system_flag")

    # Règles de base
    # 1) Cas EMERGENCY fort : gouvernance hard_block OU risk_on_off=off
    emergency = False
    degraded = False
    can_trade_global = True

    if gov_flag == "hard_block":
        emergency = True
        can_trade_global = False
        root_causes.append("governance.flag=hard_block")

    if risk_on_off == "off":
        emergency = True
        can_trade_global = False
        root_causes.append("risk_on_off=off")

    # 2) Cas stress critique
    if stress_flag in ("critical", "breach"):
        emergency = True
        can_trade_global = False
        root_causes.append(f"stress_test.global_flag={stress_flag}")

    # 3) Backpressure en mode degraded/safe/emergency
    if bp_mode in ("degraded", "safe", "emergency"):
        degraded = True
        can_trade_global = False
        root_causes.append(f"backpressure.mode={bp_mode}")

    # 4) Orchestrator en emergency / degraded
    if orch_mode == "emergency":
        emergency = True
        can_trade_global = False
        root_causes.append("orchestrator.mode=emergency")
    elif orch_mode == "degraded":
        degraded = True
        root_causes.append("orchestrator.mode=degraded")

    # 5) Risk mode reduced + size_factor 0 → quasi arrêt
    if risk_mode == "reduced" and (size_factor == 0 or size_factor == 0.0):
        degraded = True
        root_causes.append("risk_mode=reduced & size_factor=0")

    # 6) Metrics system_flag si présent
    if isinstance(system_flag_metrics, str):
        if system_flag_metrics == "critical":
            emergency = True
            can_trade_global = False
            root_causes.append("system_metrics.system_flag=critical")
        elif system_flag_metrics == "warning":
            degraded = True
            root_causes.append("system_metrics.system_flag=warning")

    # Détermination finale du mode / system_flag
    if emergency:
        mode = "emergency"
        system_flag = "critical"
        can_trade_global = False
    elif degraded:
        mode = "degraded"
        system_flag = "warning"
        can_trade_global = False
    else:
        # cas normal
        mode = "normal"
        system_flag = "ok"
        can_trade_global = bool(orch_can_trade) if orch_can_trade is not None else True

    # Si aucune root cause explicite mais mode non-normal
    if mode != "normal" and not root_causes:
        root_causes.append("unknown_cause")

    return mode, can_trade_global, system_flag, root_causes


def _build_recommendations(
    mode: str, system_flag: str, root_causes: List[str]
) -> List[str]:
    """
    Génère une liste de recommandations lisibles.
    """
    recs: List[str] = []

    if mode == "emergency":
        recs.append("Maintenir le kill-switch global et empêcher toute exécution réelle.")
        recs.append("Analyser en priorité les causes racines: " + ", ".join(root_causes))

    if "governance.flag=hard_block" in root_causes:
        recs.append("Réviser la gouvernance (governance_engine_pro) avant toute reprise.")
    if "risk_on_off=off" in root_causes:
        recs.append("Réactiver le risk engine (risk_on_off=on) uniquement après validation manuelle.")
    if any("stress_test" in c for c in root_causes):
        recs.append("Revoir les paramètres du Stress Test Engine et les limites de drawdown.")
    if any("backpressure.mode" in c for c in root_causes):
        recs.append("Analyser les logs/latences et alléger la charge pour le Backpressure Engine.")
    if any("system_metrics.system_flag" in c for c in root_causes):
        recs.append("Consulter system_metrics_pro.json pour diagnostiquer les anomalies système.")

    if not recs:
        if system_flag == "ok":
            recs.append("Aucune action immédiate requise. Continuer la surveillance.")
        elif system_flag == "warning":
            recs.append("Mode dégradé: vérifier la configuration risk/backpressure/gouvernance.")

    return recs


def main() -> None:
    logger.info("[auto_recovery_engine_pro] Démarrage de l'Auto-Recovery Engine PRO")

    # ✅ Version compatible avec ton get_data_dir actuel
    data_dir = get_data_dir()
    telemetry = _load_telemetry_files(data_dir)

    services = _compute_service_status(telemetry)
    mode, can_trade, system_flag, root_causes = _evaluate_global_state(services)
    recommendations = _build_recommendations(mode, system_flag, root_causes)

    snapshot: Dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "env": "PREPROD",
        "mode": mode,
        "system_flag": system_flag,
        "can_trade": can_trade,
        "root_causes": root_causes,
        "services": services,
        "recommendations": recommendations,
    }

    out_path = data_dir / "telemetry" / "auto_recovery_engine_pro.json"
    save_json_file(out_path, snapshot)
    logger.info(
        "[auto_recovery_engine_pro] auto_recovery_engine_pro.json sauvegardé "
        "(mode=%s, system_flag=%s, can_trade=%s)",
        mode,
        system_flag,
        can_trade,
    )

    # Publication sur le Message Bus
    severity = "info"
    if system_flag == "warning":
        severity = "warning"
    elif system_flag == "critical":
        severity = "critical"

    try:
        publish_event(
            event_type="auto_recovery.state",
            source="auto_recovery_engine_pro",
            payload={
                "timestamp": snapshot["timestamp"],
                "env": snapshot["env"],
                "mode": mode,
                "system_flag": system_flag,
                "can_trade": can_trade,
                "root_causes": root_causes,
            },
            severity=severity,
        )
        logger.info(
            "[auto_recovery_engine_pro] Event auto_recovery.state publié (severity=%s)",
            severity,
        )
    except Exception as e:
        logger.exception(
            "[auto_recovery_engine_pro] Erreur lors de la publication de l'event: %s", e
        )


if __name__ == "__main__":
    main()
