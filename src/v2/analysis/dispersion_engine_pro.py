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
# Helpers locaux pour DATA_DIR et ENV
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
# Dataclass & utilitaires
# ---------------------------------------------------------------------------

@dataclass
class DispersionMetrics:
    nb_assets: int
    dispersion_1d: Optional[float]
    share_big_movers: float
    avg_return_1d: Optional[float]


def _extract_last_return(asset_payload: Any) -> Optional[float]:
    """
    Essaie d'extraire un 'dernier retour' numérique à partir de plusieurs formats possibles.

    Formats possibles (on garde ça très permissif) :
    - float direct (asset_payload = 0.0123)
    - dict avec clé 'return_1d' ou 'last_return' ou 'r'
    - dict avec clé 'returns' (liste) → dernier élément
    """
    try:
        # Cas simple : directement un float/int
        if isinstance(asset_payload, (int, float)):
            v = float(asset_payload)
            if not math.isnan(v):
                return v
            return None

        if not isinstance(asset_payload, dict):
            return None

        for key in ("return_1d", "last_return", "r"):
            if key in asset_payload:
                v = float(asset_payload[key])
                if not math.isnan(v):
                    return v
                return None

        if "returns" in asset_payload and isinstance(asset_payload["returns"], list) and asset_payload["returns"]:
            v = float(asset_payload["returns"][-1])
            if not math.isnan(v):
                return v

    except (TypeError, ValueError):
        return None

    return None


def compute_dispersion_metrics(raw: Any) -> DispersionMetrics:
    """
    Construit les métriques de dispersion à partir d'une structure libre.

    On attend en priorité un dict du type :
    {
        "BTC": {"return_1d": 0.012, ...},
        "ETH": {"return_1d": -0.015, ...},
        ...
    }

    Mais on reste permissif (voir _extract_last_return).
    """
    if not isinstance(raw, dict):
        return DispersionMetrics(
            nb_assets=0,
            dispersion_1d=None,
            share_big_movers=0.0,
            avg_return_1d=None,
        )

    rets: List[float] = []
    for asset, payload in raw.items():
        r = _extract_last_return(payload)
        if r is None:
            continue
        rets.append(r)

    nb_assets = len(rets)
    if nb_assets == 0:
        return DispersionMetrics(
            nb_assets=0,
            dispersion_1d=None,
            share_big_movers=0.0,
            avg_return_1d=None,
        )

    if nb_assets == 1:
        dispersion = 0.0
    else:
        dispersion = statistics.pstdev(rets)

    big_movers = sum(1 for r in rets if abs(r) >= 0.05)   # >= 5%
    share_big = big_movers / nb_assets if nb_assets > 0 else 0.0
    avg_ret = sum(rets) / nb_assets

    return DispersionMetrics(
        nb_assets=nb_assets,
        dispersion_1d=dispersion,
        share_big_movers=share_big,
        avg_return_1d=avg_ret,
    )


def infer_regime_and_score(metrics: DispersionMetrics) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de dispersion cross-asset et un score simple.

    Idée :
    - Dispersion très faible -> marché "monolithique", risk_off (diversif peu efficace)
    - Dispersion élevée -> beaucoup de gagnants/perdants différents, bon terrain pour le stock picking
    """
    reasons: List[str] = []

    if metrics.nb_assets == 0 or metrics.dispersion_1d is None:
        reasons.append("Aucune donnée de dispersion exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    disp = metrics.dispersion_1d
    share_big = metrics.share_big_movers

    # Seuils simples en daily returns (en fraction, ex: 0.05 = 5 %)
    if disp <= 0.02 and share_big < 0.10:
        regime = "low_dispersion"
        global_flag = "risk_off"
        score = 35.0
        reasons.append(
            f"Dispersion très faible (σ≈{disp:.3f}), peu de gros mouvements "
            f"(|r|≥5%) : {share_big*100:.0f} % des actifs."
        )
    elif disp >= 0.08 and share_big >= 0.40:
        regime = "high_dispersion"
        global_flag = "risk_on"
        score = 70.0
        reasons.append(
            f"Dispersion élevée (σ≈{disp:.3f}), beaucoup de gros mouvements "
            f"(|r|≥5%) : {share_big*100:.0f} % des actifs."
        )
    else:
        regime = "normal"
        global_flag = "neutral"
        score = 55.0
        reasons.append(
            f"Dispersion modérée (σ≈{disp:.3f}), part de gros mouvements "
            f"(|r|≥5%) : {share_big*100:.0f} % des actifs."
        )

    if metrics.avg_return_1d is not None:
        reasons.append(
            f"Rendement moyen cross-section ≈ {metrics.avg_return_1d*100:.1f} %."
        )

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    """Map simple flag → sévérité d'event."""
    if global_flag == "risk_off":
        return "critical"
    if global_flag == "caution":
        return "warning"
    return "info"


def build_dispersion_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de dispersion cross-asset à partir de :

    data/analysis/asset_returns.json

    Formats acceptés :
    - Dict directement exploitable (voir compute_dispersion_metrics)
    - Dict avec clé 'returns' :
      { "timestamp": "...", "returns": { "BTC": {...}, "ETH": {...} } }
    """
    src_file = data_dir / "analysis" / "asset_returns.json"
    raw = load_json_file(src_file, default={})

    if isinstance(raw, dict) and "returns" in raw and isinstance(raw["returns"], dict):
        payload = raw["returns"]
    else:
        payload = raw

    metrics = compute_dispersion_metrics(payload)
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
            "dispersion_1d": metrics.dispersion_1d,
            "share_big_movers": metrics.share_big_movers,
            "avg_return_1d": metrics.avg_return_1d,
        },
        "reasons": reasons,
    }

    logger.info(
        "[dispersion_engine_pro] env=%s, regime=%s, global_flag=%s, "
        "score=%.2f, nb_assets=%d, dispersion_1d=%s, share_big_movers=%.2f",
        env,
        regime,
        global_flag,
        score,
        metrics.nb_assets,
        f"{metrics.dispersion_1d:.3f}" if metrics.dispersion_1d is not None else "None",
        metrics.share_big_movers,
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[dispersion_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_dispersion_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "dispersion_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[dispersion_engine_pro] dispersion_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication dans l’event bus
    publish_event(
        event_type="dispersion.cross_section.state",
        source="dispersion_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[dispersion_engine_pro] Event dispersion.cross_section.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
