from __future__ import annotations

import os
import math
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
# Dataclass & utilitaires Liquidity Migration
# ---------------------------------------------------------------------------

@dataclass
class LiquidityMigrationMetrics:
    nb_buckets: int
    net_pulse: Optional[float]              # [-1 ; +1] global
    share_into_risk: Optional[float]       # [0 ; 1] proportion de flux vers les buckets "risk"
    share_into_safety: Optional[float]     # [0 ; 1] proportion de flux vers les buckets "safety"


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def compute_liquidity_migration_metrics(raw: Any) -> LiquidityMigrationMetrics:
    """
    Construit les métriques de migration de liquidité à partir d'une structure libre.

    Structure recommandée (mais non obligatoire) :

    {
      "buckets": {
        "crypto_high_beta": {"flow_score": 0.6, "bucket_type": "risk"},
        "growth_equities": {"flow_score": 0.4, "bucket_type": "risk"},
        "treasuries": {"flow_score": 0.7, "bucket_type": "safety"},
        ...
      }
    }

    - flow_score ∈ [-1 ; +1] (positif = afflux, négatif = fuite)
    - bucket_type ∈ {"risk", "safety", "neutral"} (ou absent → neutral par défaut)
    """
    if isinstance(raw, dict) and isinstance(raw.get("buckets"), dict):
        buckets = raw["buckets"]
    elif isinstance(raw, dict):
        buckets = raw
    else:
        return LiquidityMigrationMetrics(
            nb_buckets=0,
            net_pulse=None,
            share_into_risk=0.0,
            share_into_safety=0.0,
        )

    flows: List[float] = []
    nb_risk_inflows = 0
    nb_safety_inflows = 0
    nb_typed = 0

    for name, payload in buckets.items():
        if not isinstance(payload, dict):
            continue

        flow = _get_float(payload.get("flow_score"))
        if flow is None:
            continue

        flows.append(flow)

        bucket_type = (payload.get("bucket_type") or payload.get("type") or "neutral").lower()
        if bucket_type in ("risk", "safety"):
            nb_typed += 1
            if flow > 0:
                if bucket_type == "risk":
                    nb_risk_inflows += 1
                elif bucket_type == "safety":
                    nb_safety_inflows += 1

    nb_buckets = len(flows)
    if nb_buckets == 0:
        return LiquidityMigrationMetrics(
            nb_buckets=0,
            net_pulse=None,
            share_into_risk=0.0,
            share_into_safety=0.0,
        )

    net_pulse = sum(flows) / nb_buckets
    if nb_typed > 0:
        share_into_risk = nb_risk_inflows / nb_typed
        share_into_safety = nb_safety_inflows / nb_typed
    else:
        share_into_risk = 0.0
        share_into_safety = 0.0

    return LiquidityMigrationMetrics(
        nb_buckets=nb_buckets,
        net_pulse=net_pulse,
        share_into_risk=share_into_risk,
        share_into_safety=share_into_safety,
    )


def infer_regime_and_score(
    metrics: LiquidityMigrationMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de migration de liquidité et un score NSC simple.

    Intuition :
    - net_pulse >> 0 + flux majoritairement vers "risk" → risk_on
    - net_pulse << 0 + flux majoritairement vers "safety" → risk_off
    - Sinon → neutral / mixed
    """
    reasons: List[str] = []

    if metrics.nb_buckets == 0 or metrics.net_pulse is None:
        reasons.append("Aucune donnée de migration de liquidité exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    p = metrics.net_pulse
    risk_share = metrics.share_into_risk or 0.0
    safety_share = metrics.share_into_safety or 0.0

    # Seuils grossiers, mais cohérents avec une logique PRO
    if p >= 0.25 and risk_share >= 0.6 and safety_share <= 0.25:
        regime = "risk_on"
        global_flag = "supportive"
        score = 72.0
        reasons.append(
            f"Forte migration vers le risque (net_pulse≈{p:.2f}, "
            f"{risk_share*100:.0f}% des flux typés vont vers les buckets 'risk')."
        )
    elif p <= -0.25 and safety_share >= 0.6:
        regime = "risk_off"
        global_flag = "risk_off"
        score = 35.0
        reasons.append(
            f"Forte migration vers la sécurité (net_pulse≈{p:.2f}, "
            f"{safety_share*100:.0f}% des flux typés vont vers les buckets 'safety')."
        )
    else:
        regime = "mixed"
        global_flag = "neutral"
        score = 55.0
        reasons.append(
            f"Migration de liquidité équilibrée ou peu directionnelle "
            f"(net_pulse≈{p:.2f}, risk≈{risk_share*100:.0f}%, safety≈{safety_share*100:.0f}%)."
        )

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    """Map simple flag → sévérité d'event."""
    if global_flag == "risk_off":
        return "critical"
    if global_flag == "supportive":
        return "info"
    if global_flag == "neutral":
        return "warning"
    if global_flag == "caution":
        return "warning"
    return "info"


def build_liquidity_migration_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de migration de liquidité à partir de :

    data/analysis/liquidity_migration.json

    Exemple de structure :

    {
      "timestamp": "...",
      "buckets": {
        "crypto_high_beta": {"flow_score": 0.6, "bucket_type": "risk"},
        "growth_equities": {"flow_score": 0.4, "bucket_type": "risk"},
        "treasuries": {"flow_score": 0.7, "bucket_type": "safety"},
        ...
      }
    }
    """
    src_file = data_dir / "analysis" / "liquidity_migration.json"
    raw = load_json_file(src_file, default={})

    metrics = compute_liquidity_migration_metrics(raw)
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
            "nb_buckets": metrics.nb_buckets,
            "net_pulse": metrics.net_pulse,
            "share_into_risk": metrics.share_into_risk,
            "share_into_safety": metrics.share_into_safety,
        },
        "reasons": reasons,
    }

    logger.info(
        "[liquidity_migration_engine_pro] env=%s, regime=%s, global_flag=%s, "
        "score=%.2f, nb_buckets=%d, net_pulse=%s, risk_share=%.2f, safety_share=%.2f",
        env,
        regime,
        global_flag,
        score,
        metrics.nb_buckets,
        f"{metrics.net_pulse:.2f}" if metrics.net_pulse is not None else "None",
        metrics.share_into_risk or 0.0,
        metrics.share_into_safety or 0.0,
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[liquidity_migration_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_liquidity_migration_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "liquidity_migration_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[liquidity_migration_engine_pro] liquidity_migration_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication event bus
    publish_event(
        event_type="liquidity.migration.state",
        source="liquidity_migration_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[liquidity_migration_engine_pro] Event liquidity.migration.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
