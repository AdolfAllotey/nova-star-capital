"""
discipline_engine_light.py

Discipline Engine (version light / Saison 1, Kernel V3)

Objectif :
    Produire un score de discipline quotidien (0–100) et un flag simple
    à partir de :
      - trading_checklist (respect du plan)
      - emotional_regime (psychologie)
      - anomaly_overview (anomalies techniques/risque)
      - logs_overview (qualité des logs / erreurs)
      - weak_signals_overview (signaux faibles à surveiller, optionnel)

Inputs attendus (tous optionnels, fallback robustes) :

  data/reports/trading_checklist.json
    {
      "score": 87.5,
      "all_ok": true,
      ...
    }

  data/analysis/emotional_regime.json
    {
      "regime": "calm" | "tilt" | "stressed" | "...",
      "score_emotional": 80.0,
      "recommended_action": "normal" | "reduce" | "pause",
      ...
    }

  data/analysis/anomaly_overview.json
    {
      "nb_anomalies": 0,
      "nb_critical": 0,
      "nb_warning": 0,
      ...
    }

  data/analysis/logs_overview.json
    {
      "flag": "ok" | "attention" | "warning" | "critical",
      "reason": "...",
      "total_counts": { ... },
      ...
    }

  data/analysis/weak_signals_overview.json (optionnel)
    {
      "nb_assets": 3,
      "nb_weak_watch": 1,
      "nb_weak_avoid": 0,
      ...
    }

Output :

  data/analysis/discipline_overview.json

Exemple de sortie :

{
  "timestamp": "...",
  "trading_date": "2025-11-30",
  "score_discipline": 82.5,
  "flag": "ok",
  "reason": "checklist_ok, emotional_calm, no_critical_anomaly",
  "components": {
    "checklist_score": 87.5,
    "emotional_score": 80.0,
    "penalty_emotional": 0.0,
    "penalty_anomaly": 0.0,
    "penalty_logs": 5.0,
    "penalty_weak_signals": 0.0
  },
  "details": {
    "checklist_all_ok": true,
    "emotional_regime": "calm",
    "emotional_action": "normal",
    "nb_anomalies": 0,
    "nb_critical": 0,
    "nb_warning": 0,
    "logs_flag": "ok",
    "logs_reason": "..."
  }
}
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("discipline_engine_light")


# ---------------------------------------------------------------------------
# Helpers ROOT/DATA autonomes
# ---------------------------------------------------------------------------


def _get_root_and_data_dirs() -> Tuple[Path, Path]:
    """
    Reconstruit ROOT_DIR et DATA_DIR à partir du chemin du fichier.

    Ce fichier vit typiquement ici :
        /opt/nsc/app/src/v2/analysis/discipline_engine_light.py

    On remonte à /opt/nsc/app (parents[3]) puis on ajoute /data.
    """
    here = Path(__file__).resolve()
    root_dir = here.parents[3]  # .../app
    data_dir = root_dir / "data"
    return root_dir, data_dir


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DisciplineComponents:
    checklist_score: float
    emotional_score: float
    penalty_emotional: float
    penalty_anomaly: float
    penalty_logs: float
    penalty_weak_signals: float


@dataclass
class DisciplineDetails:
    checklist_all_ok: bool
    emotional_regime: str
    emotional_action: str
    nb_anomalies: int
    nb_critical: int
    nb_warning: int
    logs_flag: str
    logs_reason: str


@dataclass
class DisciplineOverview:
    timestamp: str
    trading_date: str
    root_dir: str
    data_dir: str
    score_discipline: float
    flag: str  # "ok" | "review" | "warning" | "critical" | "empty"
    reason: str
    components: DisciplineComponents
    details: DisciplineDetails


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _ensure_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    return {}


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_discipline_overview() -> DisciplineOverview:
    root_dir, data_dir = _get_root_and_data_dirs()
    logger.info(
        "[discipline_engine_light] ROOT_DIR=%s, DATA_DIR=%s",
        root_dir,
        data_dir,
    )

    reports_dir = data_dir / "reports"
    analysis_dir = data_dir / "analysis"

    # 1) trading_checklist
    checklist_raw = load_json_file(reports_dir / "trading_checklist.json", default={})
    checklist = _ensure_dict(checklist_raw)
    checklist_score = _safe_float(checklist.get("score"), 0.0)
    checklist_all_ok = bool(checklist.get("all_ok", False))

    # 2) emotional_regime
    emotional_raw = load_json_file(analysis_dir / "emotional_regime.json", default={})
    emotional = _ensure_dict(emotional_raw)
    emotional_score = _safe_float(emotional.get("score_emotional"), 0.0)
    emotional_regime = str(emotional.get("regime") or "unknown")
    emotional_action = str(emotional.get("recommended_action") or "unknown")

    # 3) anomalies
    anomalies_raw = load_json_file(analysis_dir / "anomaly_overview.json", default={})
    anomalies = _ensure_dict(anomalies_raw)
    nb_anomalies = int(anomalies.get("nb_anomalies", 0) or 0)
    nb_critical = int(anomalies.get("nb_critical", 0) or 0)
    nb_warning = int(anomalies.get("nb_warning", 0) or 0)

    # 4) logs_overview
    logs_raw = load_json_file(analysis_dir / "logs_overview.json", default={})
    logs = _ensure_dict(logs_raw)
    logs_flag = str(logs.get("flag") or "unknown")
    logs_reason = str(logs.get("reason") or "")

    # 5) weak_signals_overview (optionnel)
    weak_raw = load_json_file(analysis_dir / "weak_signals_overview.json", default={})
    weak = _ensure_dict(weak_raw)
    nb_weak_watch = int(weak.get("nb_weak_watch", 0) or 0)
    nb_weak_avoid = int(weak.get("nb_weak_avoid", 0) or 0)

    # -----------------------------------------------------------------------
    # Construction du score de discipline
    # -----------------------------------------------------------------------

    # Base : checklist_score, borné à [0, 100]
    base_score = max(0.0, min(100.0, checklist_score))

    # Penalty émotionnel
    penalty_emotional = 0.0
    if emotional_regime.lower() in {"tilt", "stressed", "fear", "euphoria"}:
        penalty_emotional += 10.0
    if emotional_action in {"reduce", "pause"}:
        penalty_emotional += 5.0

    # Anomalies
    penalty_anomaly = 0.0
    if nb_critical > 0:
        penalty_anomaly += 25.0
    if nb_warning > 0:
        penalty_anomaly += 10.0

    # Logs
    penalty_logs = 0.0
    lf = logs_flag.lower()
    if lf == "attention":
        penalty_logs += 5.0
    elif lf == "warning":
        penalty_logs += 10.0
    elif lf == "critical":
        penalty_logs += 20.0

    # Weak signals : si beaucoup de signaux faibles "avoid", on réduit légèrement
    penalty_weak = 0.0
    if nb_weak_avoid >= 3:
        penalty_weak += 5.0

    total_penalty = penalty_emotional + penalty_anomaly + penalty_logs + penalty_weak

    score_discipline = max(0.0, min(100.0, base_score - total_penalty))

    # -----------------------------------------------------------------------
    # Flag global + raison
    # -----------------------------------------------------------------------
    reasons = []

    if checklist_all_ok:
        reasons.append("checklist_ok")
    else:
        reasons.append("checklist_partial")

    reasons.append(f"emotional_regime={emotional_regime}")
    reasons.append(f"anomalies_crit={nb_critical},warn={nb_warning}")
    reasons.append(f"logs_flag={logs_flag}")

    if nb_weak_avoid > 0:
        reasons.append(f"weak_avoid={nb_weak_avoid}")

    # Flag
    if checklist_score == 0.0 and emotional_score == 0.0 and nb_anomalies == 0 and logs_flag == "unknown":
        flag = "empty"
    else:
        if score_discipline >= 80.0 and nb_critical == 0 and logs_flag in {"ok", "unknown"}:
            flag = "ok"
        elif score_discipline >= 60.0 and nb_critical == 0:
            flag = "review"
        elif score_discipline >= 40.0:
            flag = "warning"
        else:
            flag = "critical"

    reason = ", ".join(reasons)

    now = datetime.now(timezone.utc)
    overview = DisciplineOverview(
        timestamp=now.isoformat(),
        trading_date=now.date().isoformat(),
        root_dir=str(root_dir),
        data_dir=str(data_dir),
        score_discipline=score_discipline,
        flag=flag,
        reason=reason,
        components=DisciplineComponents(
            checklist_score=checklist_score,
            emotional_score=emotional_score,
            penalty_emotional=penalty_emotional,
            penalty_anomaly=penalty_anomaly,
            penalty_logs=penalty_logs,
            penalty_weak_signals=penalty_weak,
        ),
        details=DisciplineDetails(
            checklist_all_ok=checklist_all_ok,
            emotional_regime=emotional_regime,
            emotional_action=emotional_action,
            nb_anomalies=nb_anomalies,
            nb_critical=nb_critical,
            nb_warning=nb_warning,
            logs_flag=logs_flag,
            logs_reason=logs_reason,
        ),
    )

    return overview


def save_discipline_overview(overview: DisciplineOverview) -> Path:
    _, data_dir = _get_root_and_data_dirs()
    output_path = data_dir / "analysis" / "discipline_overview.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = asdict(overview)
    payload["components"] = asdict(overview.components)
    payload["details"] = asdict(overview.details)

    save_json_file(output_path, payload)
    logger.info(
        "[discipline_engine_light] discipline_overview.json sauvegardé (%s, score=%.1f, flag=%s).",
        output_path,
        overview.score_discipline,
        overview.flag,
    )
    return output_path


def main() -> None:
    overview = compute_discipline_overview()
    save_discipline_overview(overview)


if __name__ == "__main__":
    main()
