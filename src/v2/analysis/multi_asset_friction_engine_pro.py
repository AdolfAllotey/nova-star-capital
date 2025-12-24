from __future__ import annotations

import os
import math
import statistics
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers env / data_dir
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """
    Renvoie le dossier data de NSC.

    - Si NSC_DATA_DIR est défini : on l'utilise.
    - Sinon : 'data' relatif au cwd (/opt/nsc/app).
    """
    base = os.getenv("NSC_DATA_DIR", "data")
    return Path(base).resolve()


def get_env() -> str:
    """Renvoie l'environnement courant ('PREPROD' par défaut)."""
    return os.getenv("NSC_ENV", "PREPROD")


# ---------------------------------------------------------------------------
# Dataclass & utilitaires de friction
# ---------------------------------------------------------------------------

@dataclass
class FrictionMetrics:
    nb_assets: int
    avg_friction_bps: Optional[float]
    max_friction_bps: Optional[float]
    share_high_friction: float  # part des actifs avec friction >= 20 bps


def _compute_asset_friction_bps(payload: Any) -> Optional[float]:
    """
    Calcule une friction totale (en bps) pour un actif à partir de plusieurs champs possibles.

    Champs supportés (si présents) :
    - 'spread_bps', 'avg_spread_bps'
    - 'slippage_bps', 'avg_slippage_bps'
    - 'fees_bps', 'fee_bps'
    - 'other_costs_bps'
    """
    try:
        if isinstance(payload, (int, float)):
            v = float(payload)
            if math.isnan(v):
                return None
            return v

        if not isinstance(payload, dict):
            return None

        total = 0.0
        keys = [
            "spread_bps",
            "avg_spread_bps",
            "slippage_bps",
            "avg_slippage_bps",
            "fees_bps",
            "fee_bps",
            "other_costs_bps",
        ]

        has_any = False
        for k in keys:
            if k in payload:
                v = float(payload[k])
                if not math.isnan(v):
                    total += v
                    has_any = True

        if not has_any:
            return None

        return total
    except (TypeError, ValueError):
        return None


def compute_friction_metrics(raw: Any) -> FrictionMetrics:
    """
    Construit les métriques de friction globale à partir d'une structure libre.

    Structure attendue (mais on reste permissif) :

    {
      "BTCUSDT": {"avg_spread_bps": 4.0, "avg_slippage_bps": 3.0, "fees_bps": 1.0},
      "ETHUSDT": {...},
      ...
    }

    ou bien :

    {
      "assets": {
        "BTCUSDT": {...},
        ...
      }
    }
    """
    if isinstance(raw, dict) and "assets" in raw and isinstance(raw["assets"], dict):
        assets_map = raw["assets"]
    elif isinstance(raw, dict):
        assets_map = raw
    else:
        return FrictionMetrics(
            nb_assets=0,
            avg_friction_bps=None,
            max_friction_bps=None,
            share_high_friction=0.0,
        )

    frictions: List[float] = []
    for asset, payload in assets_map.items():
        f = _compute_asset_friction_bps(payload)
        if f is None:
            continue
        frictions.append(f)

    nb_assets = len(frictions)
    if nb_assets == 0:
        return FrictionMetrics(
            nb_assets=0,
            avg_friction_bps=None,
            max_friction_bps=None,
            share_high_friction=0.0,
        )

    avg_friction = sum(frictions) / nb_assets
    max_friction = max(frictions)
    high_thr = 20.0  # 20 bps
    share_high = sum(1 for f in frictions if f >= high_thr) / nb_assets

    return FrictionMetrics(
        nb_assets=nb_assets,
        avg_friction_bps=avg_friction,
        max_friction_bps=max_friction,
        share_high_friction=share_high,
    )


def infer_regime_and_score(metrics: FrictionMetrics) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de friction multi-actifs et un score simple.

    Logique simple :

    - Friction faible → "low_friction" → flag = "supportive" → score élevé
    - Friction forte → "high_friction" → flag = "risk_off" → score faible
    - Entre les deux → "normal_friction" → flag = "neutral"
    """
    reasons: List[str] = []

    if metrics.nb_assets == 0 or metrics.avg_friction_bps is None:
        reasons.append("Aucune donnée de friction exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    avg_f = metrics.avg_friction_bps
    share_high = metrics.share_high_friction

    # Seuils en bps
    if avg_f <= 8.0 and share_high < 0.20:
        regime = "low_friction"
        global_flag = "supportive"
        score = 70.0
        reasons.append(
            f"Friction moyenne faible (≈{avg_f:.1f} bps), peu d'actifs à forte friction "
            f"(≥20 bps) : {share_high*100:.0f} %."
        )
    elif avg_f >= 25.0 or share_high >= 0.50:
        regime = "high_friction"
        global_flag = "risk_off"
        score = 35.0
        reasons.append(
            f"Friction moyenne élevée (≈{avg_f:.1f} bps) ou forte proportion d'actifs "
            f"à friction ≥20 bps : {share_high*100:.0f} %."
        )
    else:
        regime = "normal_friction"
        global_flag = "neutral"
        score = 55.0
        reasons.append(
            f"Friction moyenne modérée (≈{avg_f:.1f} bps), part d'actifs à friction "
            f"élevée (≥20 bps) : {share_high*100:.0f} %."
        )

    if metrics.max_friction_bps is not None:
        reasons.append(f"Friction max observée ≈ {metrics.max_friction_bps:.1f} bps.")

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    """Map simple flag → sévérité d'event."""
    if global_flag == "risk_off":
        return "critical"
    if global_flag in ("caution", "supportive"):
        return "warning" if global_flag == "caution" else "info"
    return "info"


def build_friction_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de friction multi-actifs à partir de :

    data/analysis/execution_friction.json

    Exemple de structure (non obligatoire mais recommandée) :
    {
      "timestamp": "...",
      "assets": {
        "BTCUSDT": {"avg_spread_bps": 4.0, "avg_slippage_bps": 3.0, "fees_bps": 1.0},
        "ETHUSDT": {...}
      }
    }
    """
    src_file = data_dir / "analysis" / "execution_friction.json"
    raw = load_json_file(src_file, default={})

    metrics = compute_friction_metrics(raw)
    regime, global_flag, score, reasons = infer_regime_and_score(metrics)
    severity = severity_from_flag(global_flag)

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "nb_assets": metrics.nb_assets,
            "avg_friction_bps": metrics.avg_friction_bps,
            "max_friction_bps": metrics.max_friction_bps,
            "share_high_friction": metrics.share_high_friction,
        },
        "reasons": reasons,
    }

    logger.info(
        "[multi_asset_friction_engine_pro] env=%s, regime=%s, global_flag=%s, "
        "score=%.2f, nb_assets=%d, avg_friction_bps=%s, share_high_friction=%.2f",
        env,
        regime,
        global_flag,
        score,
        metrics.nb_assets,
        f"{metrics.avg_friction_bps:.1f}" if metrics.avg_friction_bps is not None else "None",
        metrics.share_high_friction,
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[multi_asset_friction_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_friction_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "multi_asset_friction_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[multi_asset_friction_engine_pro] multi_asset_friction_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication event bus
    publish_event(
        event_type="friction.multi_asset.state",
        source="multi_asset_friction_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[multi_asset_friction_engine_pro] Event friction.multi_asset.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
