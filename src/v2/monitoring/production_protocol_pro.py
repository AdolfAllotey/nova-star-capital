# src/v2/monitoring/production_protocol_pro.py

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
    get_data_dir,
)

logger = get_logger(__name__)

# DATA_DIR dérivé de l'env (NSC_DATA_DIR) via get_data_dir()
DATA_DIR = Path(get_data_dir()).resolve()
ROOT_DIR = DATA_DIR.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Retourne un timestamp UTC ISO8601."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_analysis(name: str, default: Any) -> Any:
    """Charge un fichier JSON depuis data/analysis/<name> avec un défaut."""
    path = DATA_DIR / "analysis" / name
    return load_json_file(path, default=default)


def _load_trading(name: str, default: Any) -> Any:
    """Charge un fichier JSON depuis data/trading/<name> avec un défaut."""
    path = DATA_DIR / "trading" / name
    return load_json_file(path, default=default)


def _get_env() -> str:
    """Environnement courant (PREPROD / PROD / DEV)."""
    return os.getenv("NSC_ENV", "PREPROD").upper()


def _ensure_monitoring_dir() -> Path:
    """S'assure que data/monitoring existe."""
    mdir = DATA_DIR / "monitoring"
    mdir.mkdir(parents=True, exist_ok=True)
    return mdir


# ---------------------------------------------------------------------------
# 1) PRE-FLIGHT CHECKS
# ---------------------------------------------------------------------------


def run_preflight_checks() -> Dict[str, Any]:
    """
    Exécute les vérifications pre-flight "institutionnelles" avant la boucle :
    - lecture risk_console, kill_switch, meta_score, weak_signals, governance
    - conditions GO / NO GO
    Retourne un dict structuré avec status + raisons.
    """
    logger.info("[production_protocol] Pre-flight checks – début")

    env = _get_env()
    timestamp = _utc_now_iso()

    reasons_ok: List[str] = []
    reasons_warn: List[str] = []
    reasons_block: List[str] = []

    # -----------------------------
    # Risk Console
    # -----------------------------
    risk_console = _load_analysis("risk_console_overview.json", default={})
    risk_flag = risk_console.get("global_flag", "unknown")

    if risk_flag == "ok":
        reasons_ok.append("Risk console en mode OK.")
    elif risk_flag == "caution":
        reasons_warn.append("Risk console en mode CAUTION (prudence).")
    elif risk_flag == "danger":
        reasons_block.append("Risk console en mode DANGER – trading interdit.")
    else:
        reasons_warn.append("Risk console indisponible ou non initialisée.")

    # -----------------------------
    # Risk Engine Pro
    # -----------------------------
    risk_engine = _load_analysis("risk_engine_pro.json", default={})
    risk_stats = risk_engine.get("stats", risk_engine if isinstance(risk_engine, dict) else {})
    avg_risk_score = risk_stats.get("avg_risk_score")

    if isinstance(avg_risk_score, (int, float)):
        if avg_risk_score < 40:
            reasons_block.append(
                f"avg_risk_score={avg_risk_score:.2f} < 40 → environnement trop risqué."
            )
        elif avg_risk_score < 50:
            reasons_warn.append(
                f"avg_risk_score={avg_risk_score:.2f} → vigilance renforcée."
            )
        else:
            reasons_ok.append(
                f"avg_risk_score={avg_risk_score:.2f} compatible avec une activité prudente."
            )
    else:
        reasons_warn.append("avg_risk_score non disponible.")

    # -----------------------------
    # Meta-score Pro
    # -----------------------------
    meta = _load_analysis("meta_score_engine_pro.json", default={})
    meta_stats = meta.get("stats", meta if isinstance(meta, dict) else {})
    avg_meta_score = meta_stats.get("avg_meta_score")

    if isinstance(avg_meta_score, (int, float)):
        if avg_meta_score < 40:
            reasons_block.append(
                f"avg_meta_score={avg_meta_score:.2f} < 40 → qualité globale des signaux trop faible."
            )
        elif avg_meta_score < 50:
            reasons_warn.append(
                f"avg_meta_score={avg_meta_score:.2f} → signaux mitigés."
            )
        else:
            reasons_ok.append(
                f"avg_meta_score={avg_meta_score:.2f} → qualité globale des signaux acceptable."
            )
    else:
        reasons_warn.append("avg_meta_score non disponible.")

    # -----------------------------
    # Weak Signals Pro
    # -----------------------------
    weak = _load_analysis("weak_signals_engine_pro.json", default={})
    weak_stats = weak.get("stats", weak if isinstance(weak, dict) else {})
    nb_weak_avoid = weak_stats.get("nb_weak_avoid", 0)
    nb_weak_watch = weak_stats.get("nb_weak_watch", 0)

    if nb_weak_avoid and nb_weak_avoid > 0:
        reasons_warn.append(
            f"{nb_weak_avoid} assets en weak_avoid (signaux faibles négatifs)."
        )
    if nb_weak_watch and nb_weak_watch > 0:
        reasons_warn.append(
            f"{nb_weak_watch} assets en weak_watch (surveillance renforcée)."
        )

    # -----------------------------
    # Kill Switch Global
    # -----------------------------
    kill_switch = _load_trading("kill_switch.json", default={})
    ks_enabled = kill_switch.get("enabled", False)
    ks_mode = kill_switch.get("mode", "soft")
    ks_enriched = kill_switch.get("enriched") or {}
    ks_existing = ks_enriched.get("existing") or {}

    ks_hard_block = bool(ks_existing.get("hard_block", False))
    ks_soft_block = bool(ks_existing.get("soft_block", False) or ks_mode == "soft_block")

    if ks_hard_block:
        reasons_block.append("Kill-switch GLOBAL en HARD BLOCK.")
    elif ks_soft_block:
        reasons_warn.append("Kill-switch GLOBAL en SOFT BLOCK (prudence renforcée).")
    elif ks_enabled:
        reasons_warn.append("Kill-switch global activé en mode soft.")
    else:
        reasons_ok.append("Kill-switch global non bloquant (pas de hard block).")

    # -----------------------------
    # Governance Engine Pro
    # -----------------------------
    governance = _load_analysis("governance_engine_pro.json", default={})
    gov_stats = governance.get("stats", governance if isinstance(governance, dict) else {})
    gov_flag = gov_stats.get("flag", gov_stats.get("governance_flag", "unknown"))
    governance_score = gov_stats.get("governance_score")

    if isinstance(governance_score, (int, float)):
        if governance_score < 40:
            reasons_block.append(
                f"Governance_score={governance_score:.1f} < 40 → gouvernance insuffisante."
            )
        elif governance_score < 60:
            reasons_warn.append(
                f"Governance_score={governance_score:.1f} → renforcer la discipline."
            )
        else:
            reasons_ok.append(
                f"Governance_score={governance_score:.1f} → gouvernance acceptable."
            )
    else:
        reasons_warn.append("Governance_score indisponible.")

    if gov_flag == "hard_block":
        reasons_block.append("Governance flag=hard_block.")
    elif gov_flag == "soft_block":
        reasons_warn.append("Governance flag=soft_block (prudence).")

    # -----------------------------
    # Logs Overview
    # -----------------------------
    logs_overview = _load_analysis("logs_overview_light.json", default={})
    logs_stats = logs_overview.get("stats", logs_overview if isinstance(logs_overview, dict) else {})
    nb_errors = logs_stats.get("nb_errors", 0) or 0
    nb_warnings = logs_stats.get("nb_warnings", 0) or 0

    if nb_errors > 0:
        reasons_block.append(f"{nb_errors} erreurs détectées dans les logs (logs_overview_light).")
    if nb_warnings > 0:
        reasons_warn.append(f"{nb_warnings} warnings détectés dans les logs.")

    # -----------------------------
    # Discipline & Emotional Regime
    # -----------------------------
    discipline = _load_analysis("discipline_engine_light.json", default={})
    disc_stats = discipline.get("stats", discipline if isinstance(discipline, dict) else {})
    discipline_score = disc_stats.get("discipline_score")

    if isinstance(discipline_score, (int, float)):
        if discipline_score < 40:
            reasons_block.append(
                f"Discipline_score={discipline_score:.1f} < 40 → discipline trop faible."
            )
        elif discipline_score < 60:
            reasons_warn.append(
                f"Discipline_score={discipline_score:.1f} → renforcer la discipline."
            )
        else:
            reasons_ok.append(
                f"Discipline_score={discipline_score:.1f} → discipline satisfaisante."
            )
    else:
        reasons_warn.append("Discipline_score indisponible.")

    emotional = _load_analysis("emotional_regime_light.json", default={})
    emo_stats = emotional.get("stats", emotional if isinstance(emotional, dict) else {})
    emo_regime = emo_stats.get("regime")
    emo_reco = emo_stats.get("recommended_action") or emo_stats.get("recommended") or None

    if emo_regime:
        if emo_regime in ("panic", "tilt"):
            reasons_block.append(f"Emotional_regime={emo_regime} → trading interdit.")
        elif emo_regime in ("stressed", "euphoric"):
            reasons_warn.append(f"Emotional_regime={emo_regime} → prudence.")
        else:
            reasons_ok.append(f"Emotional_regime={emo_regime}.")
    else:
        reasons_warn.append("Emotional_regime indisponible.")

    # -----------------------------
    # Décision globale : GO / CAUTION / NO_GO
    # -----------------------------
    status: str
    mode: str

    if reasons_block:
        status = "no_go"
        mode = "blocked"
    elif reasons_warn:
        status = "caution"
        mode = "go_with_caution"
    else:
        status = "go"
        mode = "go"

    preflight = {
        "timestamp": timestamp,
        "env": env,
        "status": status,  # go / caution / no_go
        "mode": mode,
        "risk_console_flag": risk_flag,
        "avg_risk_score": avg_risk_score,
        "avg_meta_score": avg_meta_score,
        "nb_weak_avoid": nb_weak_avoid,
        "nb_weak_watch": nb_weak_watch,
        "kill_switch_hard_block": ks_hard_block,
        "kill_switch_soft_block": ks_soft_block,
        "governance_flag": gov_flag,
        "governance_score": governance_score,
        "nb_log_errors": nb_errors,
        "nb_log_warnings": nb_warnings,
        "discipline_score": discipline_score,
        "emotional_regime": emo_regime,
        "emotional_reco": emo_reco,
        "reasons_ok": reasons_ok,
        "reasons_warn": reasons_warn,
        "reasons_block": reasons_block,
    }

    # Sauvegarde preflight_report.json
    mdir = _ensure_monitoring_dir()
    preflight_path = mdir / "preflight_report.json"
    save_json_file(preflight_path, preflight)
    logger.info(
        "[production_protocol] Pre-flight report sauvegardé dans %s (status=%s)",
        preflight_path,
        status,
    )

    return preflight


# ---------------------------------------------------------------------------
# 2) RUNTIME GUARD (brique légère pour l'instant)
# ---------------------------------------------------------------------------


def runtime_guard_snapshot() -> Dict[str, Any]:
    """
    Snapshot léger du contexte runtime pour le Production Protocol.
    Pour l’instant, on se contente de relire kill_switch + risk_console.
    Option B/C pourrait ajouter latence, drawdown temps réel, etc.
    """
    timestamp = _utc_now_iso()
    env = _get_env()

    risk_console = _load_analysis("risk_console_overview.json", default={})
    risk_flag = risk_console.get("global_flag", "unknown")

    kill_switch = _load_trading("kill_switch.json", default={})
    ks_enriched = kill_switch.get("enriched") or {}
    ks_existing = ks_enriched.get("existing") or {}

    ks_mode = kill_switch.get("mode", "soft")
    ks_hard = bool(ks_existing.get("hard_block", False))
    ks_soft = bool(ks_existing.get("soft_block", False) or ks_mode == "soft_block")

    action: str
    if ks_hard:
        action = "halt_trading"
    elif ks_soft:
        action = "no_new_trades"
    else:
        action = "normal"

    snapshot = {
        "timestamp": timestamp,
        "env": env,
        "risk_console_flag": risk_flag,
        "kill_switch_mode": ks_mode,
        "kill_switch_hard_block": ks_hard,
        "kill_switch_soft_block": ks_soft,
        "execution_action": action,  # normal / no_new_trades / halt_trading
    }

    return snapshot


# ---------------------------------------------------------------------------
# 3) POST-FLIGHT CHECKS
# ---------------------------------------------------------------------------


def run_postflight_checks() -> Dict[str, Any]:
    """
    Vérifications post-flight :
    - cohérence des signaux / exécutions
    - absence d'anomalies évidentes sur les positions / fills
    """
    logger.info("[production_protocol] Post-flight checks – début")

    timestamp = _utc_now_iso()
    env = _get_env()

    execution_attempts = _load_trading("execution_attempts.json", default=[])
    simulated_fills = _load_trading("simulated_fills.json", default=[])
    open_positions = _load_trading("open_positions.json", default=[])
    exit_events = _load_trading("exit_events.json", default=[])

    # On tolère que ces fichiers soient {} ou [].
    if isinstance(execution_attempts, dict):
        execution_attempts_list = execution_attempts.get("items", [])
    else:
        execution_attempts_list = execution_attempts

    if isinstance(simulated_fills, dict):
        simulated_fills_list = simulated_fills.get("items", [])
    else:
        simulated_fills_list = simulated_fills

    if isinstance(open_positions, dict):
        open_positions_list = open_positions.get("items", [])
    else:
        open_positions_list = open_positions

    if isinstance(exit_events, dict):
        exit_events_list = exit_events.get("items", [])
    else:
        exit_events_list = exit_events

    nb_exec_attempts = len(execution_attempts_list) if isinstance(execution_attempts_list, list) else 0
    nb_fills = len(simulated_fills_list) if isinstance(simulated_fills_list, list) else 0
    nb_open_positions = len(open_positions_list) if isinstance(open_positions_list, list) else 0
    nb_exit_events = len(exit_events_list) if isinstance(exit_events_list, list) else 0

    # Sanity checks simples
    reasons_ok: List[str] = []
    reasons_warn: List[str] = []

    reasons_ok.append(
        f"Exécutions: {nb_exec_attempts} tentatives, {nb_fills} fills, {nb_open_positions} positions ouvertes, {nb_exit_events} évènements de sortie."
    )

    # Exemple de sanity check minimal : pas de weight > 1.0 si présent
    abnormal_weights = 0
    if isinstance(open_positions_list, list):
        for pos in open_positions_list:
            if not isinstance(pos, dict):
                continue
            w = pos.get("weight") or pos.get("target_weight")
            if isinstance(w, (int, float)) and w > 1.0:
                abnormal_weights += 1

    if abnormal_weights > 0:
        reasons_warn.append(f"{abnormal_weights} positions avec un weight > 1.0 détecté.")

    status = "ok" if not reasons_warn else "warning"

    postflight = {
        "timestamp": timestamp,
        "env": env,
        "status": status,  # ok / warning
        "nb_exec_attempts": nb_exec_attempts,
        "nb_fills": nb_fills,
        "nb_open_positions": nb_open_positions,
        "nb_exit_events": nb_exit_events,
        "reasons_ok": reasons_ok,
        "reasons_warn": reasons_warn,
    }

    mdir = _ensure_monitoring_dir()
    postflight_path = mdir / "postflight_report.json"
    save_json_file(postflight_path, postflight)
    logger.info(
        "[production_protocol] Post-flight report sauvegardé dans %s (status=%s)",
        postflight_path,
        status,
    )

    return postflight


# ---------------------------------------------------------------------------
# 4) ENTRYPOINT GLOBAL
# ---------------------------------------------------------------------------


def run_production_protocol() -> Dict[str, Any]:
    """
    Pipeline complet Production Protocol Pro :
    - Pre-flight checks
    - Runtime snapshot (léger)
    - Post-flight checks
    - Sauvegarde d’un rapport consolidé
    """
    logger.info(
        "[production_protocol] === Lancement Production Protocol Pro (env=%s) ===",
        _get_env(),
    )

    preflight = run_preflight_checks()
    runtime_snapshot = runtime_guard_snapshot()
    postflight = run_postflight_checks()

    global_status = {
        "preflight_status": preflight.get("status"),
        "runtime_action": runtime_snapshot.get("execution_action"),
        "postflight_status": postflight.get("status"),
    }

    report = {
        "timestamp": _utc_now_iso(),
        "env": _get_env(),
        "global_status": global_status,
        "preflight": preflight,
        "runtime_snapshot": runtime_snapshot,
        "postflight": postflight,
    }

    mdir = _ensure_monitoring_dir()
    report_path = mdir / "production_protocol_report.json"
    save_json_file(report_path, report)

    logger.info(
        "[production_protocol] Rapport complet sauvegardé dans %s (preflight=%s, runtime=%s, postflight=%s)",
        report_path,
        global_status["preflight_status"],
        global_status["runtime_action"],
        global_status["postflight_status"],
    )

    return report


def main() -> None:
    run_production_protocol()


if __name__ == "__main__":
    main()
