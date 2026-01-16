"""
kill_switch_manager.py

Kill-switch global automatique pour Nova Star Capital (version hedge fund light).

Règles v1 :
- ON si :
    * anomalies critiques détectées (nb_critical > 0)
    * OU checklist de trading non conforme avec score < 70
    * OU régime émotionnel dégradé (score_emotional <= 40)
- Sinon OFF.

Ce module est appelé par la daily_trading_loop (fin de journée) pour
mettre à jour data/trading/kill_switch.json.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("kill_switch_manager")

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"

ANOMALY_FILE = DATA_DIR / "analysis" / "anomaly_overview.json"
CHECKLIST_FILE = DATA_DIR / "reports" / "trading_checklist.json"
EMOTIONAL_FILE = DATA_DIR / "analysis" / "emotional_regime.json"
KILL_SWITCH_FILE = DATA_DIR / "trading" / "kill_switch.json"


@dataclass
class KillSwitchDecision:
    enabled: bool
    reason: str
    details: Dict[str, Any]


def _safe_load_dict(path: Path) -> Dict[str, Any]:
    data = load_json_file(path, default={})
    return data if isinstance(data, dict) else {}


def _evaluate_from_anomalies(anomaly: Dict[str, Any]) -> Optional[str]:
    nb_critical = anomaly.get("nb_critical", 0)
    nb_warning = anomaly.get("nb_warning", 0)
    nb_total = anomaly.get("nb_anomalies", nb_critical + nb_warning)

    if nb_critical > 0:
        return f"anomalies critiques détectées (critical={nb_critical}, total={nb_total})"
    return None


def _evaluate_from_checklist(checklist: Dict[str, Any]) -> Optional[str]:
    all_ok = checklist.get("all_ok", True)
    score = float(checklist.get("score", 100.0))

    if (not all_ok) and score < 70.0:
        return f"checklist non conforme (score={score:.1f}, all_ok={all_ok})"
    return None


def _evaluate_from_emotional(emotional: Dict[str, Any]) -> Optional[str]:
    score_emotional = float(emotional.get("score_emotional", 80.0))
    regime = emotional.get("regime", "unknown")
    action = emotional.get("recommended_action", "normal")

    # Seuil simple : si score <= 40 → on stoppe
    if score_emotional <= 40.0 or action in ("pause", "stop"):
        return (
            f"régime émotionnel dégradé (score={score_emotional:.1f}, "
            f"regime={regime}, action={action})"
        )
    return None


def decide_kill_switch() -> KillSwitchDecision:
    """Calcule la décision de kill-switch à partir des fichiers d'analyse."""

    anomaly = _safe_load_dict(ANOMALY_FILE)
    checklist = _safe_load_dict(CHECKLIST_FILE)
    emotional = _safe_load_dict(EMOTIONAL_FILE)

    reasons = []

    r_anom = _evaluate_from_anomalies(anomaly)
    if r_anom:
        reasons.append(r_anom)

    r_chk = _evaluate_from_checklist(checklist)
    if r_chk:
        reasons.append(r_chk)

    r_emo = _evaluate_from_emotional(emotional)
    if r_emo:
        reasons.append(r_emo)

    if reasons:
        enabled = True
        reason = " / ".join(reasons)
    else:
        enabled = False
        reason = "ok"

    details = {
        "anomaly_overview": {
            "nb_anomalies": anomaly.get("nb_anomalies", 0),
            "nb_critical": anomaly.get("nb_critical", 0),
            "nb_warning": anomaly.get("nb_warning", 0),
        },
        "checklist": {
            "all_ok": checklist.get("all_ok", True),
            "score": checklist.get("score", 100.0),
        },
        "emotional_regime": {
            "regime": emotional.get("regime", "unknown"),
            "score_emotional": emotional.get("score_emotional", 80.0),
            "recommended_action": emotional.get("recommended_action", "normal"),
        },
    }

    return KillSwitchDecision(enabled=enabled, reason=reason, details=details)


def apply_kill_switch(decision: KillSwitchDecision) -> None:
    """Écrit data/trading/kill_switch.json en fonction de la décision."""

    payload: Dict[str, Any] = {
        "enabled": decision.enabled,
        "reason": decision.reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "details": decision.details,
    }

    KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    save_json_file(KILL_SWITCH_FILE, payload)

    logger.info(
        "[kill_switch_manager] Kill-switch updated: enabled=%s, reason=%s",
        decision.enabled,
        decision.reason,
    )


def main() -> None:
    logger.info(
        "[kill_switch_manager] ROOT_DIR=%s, DATA_DIR=%s",
        ROOT_DIR,
        DATA_DIR,
    )
    decision = decide_kill_switch()
    apply_kill_switch(decision)


if __name__ == "__main__":
    main()
