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
# Dataclass & utilitaires de calcul
# ---------------------------------------------------------------------------

@dataclass
class CorrelationMetrics:
    nb_pairs: int
    avg_abs_corr: Optional[float]
    avg_pos_corr: Optional[float]
    avg_neg_corr: Optional[float]
    share_high_corr: float
    share_strong_neg: float


def _safe_append(values: List[float], value: Any) -> None:
    """Ajoute une valeur numérique à une liste si elle est valide."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return

    if math.isnan(v):
        return

    # Corrélation bornée dans [-1, 1]
    v = max(-1.0, min(1.0, v))
    values.append(v)


def compute_correlation_metrics(matrix: Dict[str, Dict[str, Any]]) -> CorrelationMetrics:
    """
    Calcule quelques métriques globales à partir d'une matrice de corrélation.

    matrix est supposée être du type :
    {
        "BTC": {"ETH": 0.8, "SOL": 0.6},
        "ETH": {"BTC": 0.8, "SOL": 0.5},
        ...
    }
    On ne compte chaque paire qu'une seule fois.
    """
    assets = sorted(matrix.keys())
    vals: List[float] = []
    pos_vals: List[float] = []
    neg_vals: List[float] = []

    nb_high_corr = 0       # |corr| >= 0.7
    nb_strong_neg = 0      # corr <= -0.5
    nb_pairs = 0

    for i, a in enumerate(assets):
        row = matrix.get(a, {})
        for b in assets[i + 1 :]:
            tmp: List[float] = []
            corr_raw = row.get(b)
            _safe_append(tmp, corr_raw)

            if not tmp:
                corr_raw = matrix.get(b, {}).get(a)
                _safe_append(tmp, corr_raw)

            if not tmp:
                continue

            corr = tmp[0]
            nb_pairs += 1
            vals.append(abs(corr))
            if corr >= 0:
                pos_vals.append(corr)
            else:
                neg_vals.append(corr)

            if abs(corr) >= 0.7:
                nb_high_corr += 1
            if corr <= -0.5:
                nb_strong_neg += 1

    if nb_pairs == 0:
        return CorrelationMetrics(
            nb_pairs=0,
            avg_abs_corr=None,
            avg_pos_corr=None,
            avg_neg_corr=None,
            share_high_corr=0.0,
            share_strong_neg=0.0,
        )

    def _avg(xs: List[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    return CorrelationMetrics(
        nb_pairs=nb_pairs,
        avg_abs_corr=_avg(vals),
        avg_pos_corr=_avg(pos_vals),
        avg_neg_corr=_avg(neg_vals),
        share_high_corr=nb_high_corr / nb_pairs if nb_pairs > 0 else 0.0,
        share_strong_neg=nb_strong_neg / nb_pairs if nb_pairs > 0 else 0.0,
    )


def infer_regime_and_score(metrics: CorrelationMetrics) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime global + flag de risque + score simple à partir des métriques.
    Retourne (regime, global_flag, score, reasons)
    """
    reasons: List[str] = []

    if metrics.nb_pairs == 0 or metrics.avg_abs_corr is None:
        reasons.append("Aucune donnée de corrélation exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    avg_abs = metrics.avg_abs_corr
    share_high = metrics.share_high_corr
    share_strong_neg = metrics.share_strong_neg

    if avg_abs >= 0.8 and share_high >= 0.6:
        regime = "panic"
        global_flag = "risk_off"
        score = 20.0
        reasons.append(
            f"Corrélation moyenne très élevée (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% des paires en corrélation forte."
        )
    elif avg_abs >= 0.6:
        regime = "high_corr"
        global_flag = "caution"
        score = 35.0
        reasons.append(
            f"Corrélation moyenne élevée (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% des paires en corrélation forte."
        )
    elif avg_abs >= 0.35:
        regime = "normal"
        global_flag = "neutral"
        score = 55.0
        reasons.append(
            f"Corrélations modérées (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% de corrélations fortes."
        )
    else:
        regime = "diversified"
        global_flag = "risk_on"
        score = 70.0
        reasons.append(
            f"Corrélations globalement faibles (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% de corrélations fortes."
        )

    if share_strong_neg > 0.2:
        reasons.append(
            f"Part importante de corrélations fortement négatives "
            f"({share_strong_neg*100:.0f}% des paires ≤ -0.5)."
        )

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    """Map simple flag → sévérité d'event."""
    if global_flag == "risk_off":
        return "critical"
    if global_flag == "caution":
        return "warning"
    return "info"


def build_correlation_regime_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de régime de corrélation global à partir d'un fichier JSON.

    Fichier attendu : data/analysis/asset_correlations.json

    Deux formats possibles :
    1) Directement la matrice :
       { "BTC": {"ETH": 0.8, "SOL": 0.6}, ... }
    2) Emballé :
       { "timestamp": "...", "matrix": { ... } }
    """
    corr_file = data_dir / "analysis" / "asset_correlations.json"
    raw = load_json_file(corr_file, default={})

    if isinstance(raw, dict) and "matrix" in raw and isinstance(raw["matrix"], dict):
        matrix = raw["matrix"]
    else:
        matrix = raw if isinstance(raw, dict) else {}

    metrics = compute_correlation_metrics(matrix)
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
            "nb_pairs": metrics.nb_pairs,
            "avg_abs_corr": metrics.avg_abs_corr,
            "avg_pos_corr": metrics.avg_pos_corr,
            "avg_neg_corr": metrics.avg_neg_corr,
            "share_high_corr": metrics.share_high_corr,
            "share_strong_neg": metrics.share_strong_neg,
        },
        "reasons": reasons,
    }

    logger.info(
        "[correlation_regime_engine_pro] env=%s, regime=%s, global_flag=%s, "
        "score=%.2f, nb_pairs=%d, avg_abs_corr=%s",
        env,
        regime,
        global_flag,
        score,
        metrics.nb_pairs,
        f"{metrics.avg_abs_corr:.2f}" if metrics.avg_abs_corr is not None else "None",
    )

    return state, severity


def main() -> None:
    data_dir: Path = get_data_dir()
    env: str = get_env()

    logger.info(
        "[correlation_regime_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_correlation_regime_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "correlation_regime_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[correlation_regime_engine_pro] correlation_regime_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication dans l’event bus
    publish_event(
        event_type="correlation.regime.state",
        source="correlation_regime_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[correlation_regime_engine_pro] Event correlation.regime.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
