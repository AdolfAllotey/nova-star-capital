# src/v2/analysis/meta_score_engine_pro.py
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

logger = get_logger("meta_score_engine_pro")


# ---------------------------------------------------------------------------
# Env / Paths
# ---------------------------------------------------------------------------

def _now_ts() -> int:
    return int(time.time())


def _get_env() -> str:
    return os.environ.get("NSC_ENV", "PREPROD")


def _get_data_dir() -> Path:
    root = os.environ.get("NSC_ROOT_DIR") or os.getcwd()
    return Path(os.environ.get("NSC_DATA_DIR", str(Path(root) / "data")))


def _analysis_dir(data_dir: Path) -> Path:
    return data_dir / "analysis"


def _telemetry_dir(data_dir: Path) -> Path:
    return data_dir / "telemetry"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _score_01(x: Any, default: float = 0.5) -> float:
    """
    Accepte:
    - score déjà en 0..1
    - score en 0..100
    - None -> default
    """
    v = _safe_float(x, default)
    if v > 1.0:
        v = v / 100.0
    return _clamp(v, 0.0, 1.0)


def _score_100(x: Any, default: float = 50.0) -> float:
    """
    Accepte:
    - score en 0..100
    - score en 0..1
    """
    v = _safe_float(x, default)
    if v <= 1.0:
        v = v * 100.0
    return _clamp(v, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any) -> Any:
    return load_json_file(path, default=default)


def _read_engine_score(payload: Any, keys: Tuple[str, ...]) -> Optional[float]:
    """
    Extrait un score à partir d'un JSON de moteur.
    keys: chemins possibles "score", "avg", etc.
    """
    if not isinstance(payload, dict):
        return None
    for k in keys:
        v = payload.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _severity_from_score(score_100: float) -> str:
    if score_100 >= 75:
        return "info"
    if score_100 >= 55:
        return "warning"
    return "critical"


def _publish_event(event_type: str, source: str, severity: str, payload: Dict[str, Any]) -> None:
    """
    Publication best-effort (MessageBus / MessageBusPro si dispo).
    """
    try:
        from src.v2.core.message_bus import MessageBus  # type: ignore
        mb = MessageBus()
        mb.publish(event_type, source, severity, payload)
        return
    except Exception:
        pass

    try:
        from src.v2.core.message_bus_pro import MessageBusPro  # type: ignore
        mb = MessageBusPro()
        mb.publish(event_type, source, severity, payload)
        return
    except Exception:
        pass

    # Si aucun bus n'est dispo, on ne crash pas.
    logger.debug("[meta_score_engine_pro] EventBus indisponible (skip publish)")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _default_components() -> List[Dict[str, Any]]:
    """
    Liste des moteurs "score" qu'on agrège.
    Chaque moteur peut ne pas exister -> on ignore proprement.
    """
    return [
        {
            "name": "signal_quality_engine_pro",
            "file": "signal_quality_engine_pro.json",
            "score_keys": ("score", "avg_score", "avg"),
            "weight": 0.30,
        },
        {
            "name": "market_conditions_engine_pro",
            "file": "market_conditions_engine_pro.json",
            "score_keys": ("score",),
            "weight": 0.25,
        },
        {
            "name": "volatility_state_machine_pro",
            "file": "volatility_state_machine_pro.json",
            "score_keys": ("score", "value"),
            "weight": 0.15,
        },
        {
            "name": "market_coherence_engine_pro",
            "file": "market_coherence_engine_pro.json",
            "score_keys": ("score",),
            "weight": 0.15,
        },
        {
            "name": "risk_engine_pro",
            "file": "risk_engine_pro.json",
            "score_keys": ("score", "risk_score"),
            "weight": 0.15,
        },
    ]


def compute_meta_score(analysis_dir: Path, components_cfg: List[Dict[str, Any]]) -> Dict[str, Any]:
    loaded: List[Dict[str, Any]] = []
    reasons: List[str] = []

    weighted_sum = 0.0
    weight_sum = 0.0

    for cfg in components_cfg:
        name = str(cfg["name"])
        file_name = str(cfg["file"])
        weight = _safe_float(cfg.get("weight", 0.0), 0.0)
        score_keys = tuple(cfg.get("score_keys", ("score",)))

        path = analysis_dir / file_name
        payload = _load_json(path, default={})

        score = _read_engine_score(payload, score_keys)
        if score is None:
            reasons.append(f"{name}: missing_score ({file_name})")
            loaded.append({
                "name": name,
                "file": file_name,
                "weight": weight,
                "present": path.exists(),
                "score": None,
            })
            continue

        score100 = _score_100(score, default=50.0)

        # accumulate
        if weight > 0:
            weighted_sum += score100 * weight
            weight_sum += weight

        loaded.append({
            "name": name,
            "file": file_name,
            "weight": weight,
            "present": path.exists(),
            "score": round(score100, 2),
        })

    if weight_sum <= 0:
        meta_score = 50.0
        reasons.append("no_component_scores -> meta_score=50")
    else:
        meta_score = weighted_sum / weight_sum

    meta_score = _clamp(meta_score, 0.0, 100.0)

    # Flag simple (pour orchestrator/kill-switch si besoin)
    flag = "neutral"
    if meta_score >= 70:
        flag = "risk_on"
    elif meta_score <= 35:
        flag = "risk_off"

    return {
        "timestamp": _now_ts(),
        "env": _get_env(),
        "score": round(meta_score, 2),
        "avg": round(meta_score, 2),  # compat (market_regime_detector lit parfois avg)
        "flag": flag,
        "metrics": {
            "nb_components": len(components_cfg),
            "nb_with_score": sum(1 for x in loaded if isinstance(x.get("score"), (int, float))),
            "weight_sum": round(weight_sum, 4),
        },
        "components": loaded,
        "reasons": reasons,
    }


def main() -> None:
    data_dir = _get_data_dir()
    env = _get_env()

    analysis_dir = _analysis_dir(data_dir)
    telemetry_dir = _telemetry_dir(data_dir)

    ensure_dir(str(data_dir))
    ensure_dir(str(analysis_dir))
    ensure_dir(str(telemetry_dir))

    logger.info("[meta_score_engine_pro] DATA_DIR=%s, env=%s", str(data_dir), env)

    cfg = _default_components()
    state = compute_meta_score(analysis_dir=analysis_dir, components_cfg=cfg)

    out_path = analysis_dir / "meta_score_engine_pro.json"
    save_json_file(out_path, state)

    severity = _severity_from_score(state["score"])
    try:
        _publish_event(
            event_type="meta.score.state",
            source="meta_score_engine_pro",
            severity=severity,
            payload=state,
        )
    except Exception as exc:
        logger.warning("[meta_score_engine_pro] publish_event failed: %s", exc)

    logger.info(
        "[meta_score_engine_pro] OK score=%.2f flag=%s -> %s",
        state["score"], state["flag"], str(out_path),
    )


if __name__ == "__main__":
    main()
