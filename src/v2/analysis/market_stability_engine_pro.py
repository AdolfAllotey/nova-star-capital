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
# Dataclass & helpers
# ---------------------------------------------------------------------------

@dataclass
class MarketStabilityMetrics:
    """
    Métriques de stabilité globale du marché.

    Fichier attendu : data/analysis/market_stability.json

    Exemple de format (souple) :

    {
      "stability_score": 0.55,          # 0–1, 1 = très stable, 0 = très instable
      "fragility_score": 0.3,          # 0–1, 1 = très fragile
      "crash_risk_score": 0.25,        # 0–1, 1 = risque élevé
      "liquidity_fragility_score": 0.35,
      "correlation_cluster_score": 0.6,
      "volatility_regime_score": 0.5,
      "tail_risk_score": 0.4,
      "stress_events_rolling": 3,
      "nb_assets": 450
    }
    """

    stability_score: Optional[float]
    fragility_score: Optional[float]
    crash_risk_score: Optional[float]
    liquidity_fragility_score: Optional[float]
    correlation_cluster_score: Optional[float]
    volatility_regime_score: Optional[float]
    tail_risk_score: Optional[float]
    stress_events_rolling: Optional[int]
    nb_assets: Optional[int]


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _get_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_market_stability_metrics(raw: Any) -> MarketStabilityMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return MarketStabilityMetrics(
        stability_score=_get_float(raw.get("stability_score")),
        fragility_score=_get_float(raw.get("fragility_score")),
        crash_risk_score=_get_float(raw.get("crash_risk_score")),
        liquidity_fragility_score=_get_float(raw.get("liquidity_fragility_score")),
        correlation_cluster_score=_get_float(raw.get("correlation_cluster_score")),
        volatility_regime_score=_get_float(raw.get("volatility_regime_score")),
        tail_risk_score=_get_float(raw.get("tail_risk_score")),
        stress_events_rolling=_get_int(raw.get("stress_events_rolling")),
        nb_assets=_get_int(raw.get("nb_assets")),
    )


# ---------------------------------------------------------------------------
# Logique Market Stability
# ---------------------------------------------------------------------------

def infer_market_stability_regime_and_score(
    m: MarketStabilityMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de Market Stability + flag global + score NSC.

    Intuition :

    - Marché stable / résilient :
        stabilité élevée, fragilité/crash/liquidity fragility faibles
        → regime="stable", global_flag="supportive"/"neutral", score > 55
    - Marché fragile / instable :
        fragilité/crash/liquidity fragility élevées
        → regime="fragile" ou "unstable", global_flag="risk_off", score < 45
    - Sinon : regime="mixed", global_flag="caution", score ≈ 50
    """

    reasons: List[str] = []

    stability = m.stability_score
    fragility = m.fragility_score
    crash_risk = m.crash_risk_score
    liq_frag = m.liquidity_fragility_score
    corr_cluster = m.correlation_cluster_score
    vol_regime = m.volatility_regime_score
    tail_risk = m.tail_risk_score
    stress_events = m.stress_events_rolling
    nb_assets = m.nb_assets

    # Valeurs "positives" (stability / volatility_regime)
    positives = [v for v in (stability, vol_regime) if v is not None]
    # Valeurs "risque" (fragility, crash, liquidity, tail, corr_cluster)
    risks = [
        v
        for v in (
            fragility,
            crash_risk,
            liq_frag,
            tail_risk,
            corr_cluster,
        )
        if v is not None
    ]

    if not positives and not risks:
        reasons.append("Aucune donnée de Market Stability exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    HIGH = 0.7
    MED = 0.5
    LOW = 0.3

    regime = "mixed"
    global_flag = "caution"
    score = 50.0

    # ------------------------------------------------------------------
    # 1) Cas "stable"
    # ------------------------------------------------------------------
    stable_conditions = 0
    expl_stable: List[str] = []

    if stability is not None and stability >= HIGH:
        stable_conditions += 1
        expl_stable.append(f"stability_score={stability:.2f}")
    if vol_regime is not None and vol_regime >= MED:
        stable_conditions += 1
        expl_stable.append(f"volatility_regime_score={vol_regime:.2f}")

    low_risk_conditions = 0
    if fragility is not None and fragility <= LOW:
        low_risk_conditions += 1
        expl_stable.append(f"fragility_score={fragility:.2f}")
    if crash_risk is not None and crash_risk <= LOW:
        low_risk_conditions += 1
        expl_stable.append(f"crash_risk_score={crash_risk:.2f}")
    if liq_frag is not None and liq_frag <= LOW:
        low_risk_conditions += 1
        expl_stable.append(f"liquidity_fragility_score={liq_frag:.2f}")
    if tail_risk is not None and tail_risk <= LOW:
        low_risk_conditions += 1
        expl_stable.append(f"tail_risk_score={tail_risk:.2f}")

    # quelques stress events sont tolérés, mais pas trop
    if stress_events is not None and stress_events <= 1:
        stable_conditions += 1
        expl_stable.append(f"stress_events_rolling={stress_events}")

    if stable_conditions >= 2 and low_risk_conditions >= 2:
        regime = "stable"
        global_flag = "neutral"

        # Score : base sur la stabilité – pénalité légère si quelques risques
        core_vals = []
        if stability is not None:
            core_vals.append(stability)
        if vol_regime is not None:
            core_vals.append(vol_regime)
        avg_core = sum(core_vals) / len(core_vals) if core_vals else MED

        risk_penalty = 0.0
        for v in risks:
            if v > MED:
                risk_penalty += (v - MED) * 0.2  # pénalité légère

        score = 60.0 + (avg_core - MED) * 30.0 - risk_penalty * 20.0
        score = max(50.0, min(75.0, score))

        msg = (
            "MARKET STABILITY – STABLE : conditions structurellement plutôt "
            "stables et résilientes, sans signaux majeurs de fragilité."
        )
        if nb_assets is not None:
            expl_stable.append(f"nb_assets={nb_assets}")
        if expl_stable:
            msg += " " + ", ".join(expl_stable)

        # Si tous les indicateurs de risque sont très bas → vraiment "supportive"
        if all(v is not None and v <= LOW for v in risks) and stability and stability >= HIGH:
            global_flag = "supportive"
            score = max(score, 70.0)
            msg += " Niveau de stabilité élevé et faible fragilité globale."

        reasons.append(msg)
        return regime, global_flag, score, reasons

    # ------------------------------------------------------------------
    # 2) Cas "fragile / unstable"
    # ------------------------------------------------------------------
    frag_conditions = 0
    expl_frag: List[str] = []

    if stability is not None and stability <= LOW:
        frag_conditions += 1
        expl_frag.append(f"stability_score={stability:.2f}")
    if fragility is not None and fragility >= HIGH:
        frag_conditions += 1
        expl_frag.append(f"fragility_score={fragility:.2f}")
    if crash_risk is not None and crash_risk >= HIGH:
        frag_conditions += 1
        expl_frag.append(f"crash_risk_score={crash_risk:.2f}")
    if liq_frag is not None and liq_frag >= HIGH:
        frag_conditions += 1
        expl_frag.append(f"liquidity_fragility_score={liq_frag:.2f}")
    if tail_risk is not None and tail_risk >= HIGH:
        frag_conditions += 1
        expl_frag.append(f"tail_risk_score={tail_risk:.2f}")
    if corr_cluster is not None and corr_cluster >= HIGH:
        frag_conditions += 1
        expl_frag.append(f"correlation_cluster_score={corr_cluster:.2f}")

    if stress_events is not None and stress_events >= 3:
        frag_conditions += 1
        expl_frag.append(f"stress_events_rolling={stress_events}")

    if frag_conditions >= 3:
        regime = "fragile"
        global_flag = "risk_off"

        # Score : base basse, plus les risques sont élevés plus on descend
        risk_avg = sum(risks) / len(risks) if risks else 0.7
        score = 45.0 - (risk_avg - MED) * 30.0
        score = max(25.0, min(45.0, score))

        msg = (
            "MARKET STABILITY – FRAGILE : accumulation de signaux de stress "
            "et de fragilité structurelle, risque de rupture accru."
        )
        if nb_assets is not None:
            expl_frag.append(f"nb_assets={nb_assets}")
        if expl_frag:
            msg += " " + ", ".join(expl_frag)

        reasons.append(msg)
        return regime, global_flag, score, reasons

    # ------------------------------------------------------------------
    # 3) Cas "mixed"
    # ------------------------------------------------------------------
    regime = "mixed"
    global_flag = "caution"

    # Score : neutral autour de 50, modulé par l'équilibre stabilité / risques
    avg_stab = None
    if positives:
        avg_stab = sum(positives) / len(positives)

    avg_risk = None
    if risks:
        avg_risk = sum(risks) / len(risks)

    score = 50.0
    details: List[str] = []

    if avg_stab is not None:
        details.append(f"avg_stability={avg_stab:.2f}")
        score += (avg_stab - MED) * 10.0
    if avg_risk is not None:
        details.append(f"avg_risk={avg_risk:.2f}")
        score -= max(0.0, avg_risk - MED) * 10.0
    if stress_events is not None:
        details.append(f"stress_events={stress_events}")
        if stress_events >= 3:
            score -= 5.0
        elif stress_events == 0:
            score += 3.0

    score = max(35.0, min(65.0, score))

    if nb_assets is not None:
        details.append(f"nb_assets={nb_assets}")

    msg = (
        "MARKET STABILITY – MIXED : certains signaux de stabilité, mais aussi "
        "des éléments de fragilité. Prudence recommandée."
    )
    if details:
        msg += " " + ", ".join(details)

    reasons.append(msg)
    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    if global_flag in ("supportive", "neutral"):
        return "info"
    if global_flag == "caution":
        return "warning"
    if global_flag == "risk_off":
        return "critical"
    return "info"


def build_market_stability_state(
    data_dir: Path,
    env: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état Market Stability à partir de :

    data/analysis/market_stability.json
    """

    src_file = data_dir / "analysis" / "market_stability.json"
    raw = load_json_file(src_file, default={})

    metrics = load_market_stability_metrics(raw)
    regime, global_flag, score, reasons = infer_market_stability_regime_and_score(
        metrics
    )

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "stability_score": metrics.stability_score,
            "fragility_score": metrics.fragility_score,
            "crash_risk_score": metrics.crash_risk_score,
            "liquidity_fragility_score": metrics.liquidity_fragility_score,
            "correlation_cluster_score": metrics.correlation_cluster_score,
            "volatility_regime_score": metrics.volatility_regime_score,
            "tail_risk_score": metrics.tail_risk_score,
            "stress_events_rolling": metrics.stress_events_rolling,
            "nb_assets": metrics.nb_assets,
        },
        "reasons": reasons,
    }

    severity = severity_from_flag(global_flag)
    return state, severity


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    data_dir = get_data_dir()
    env = get_env()
    logger.info(
        "[market_stability_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_market_stability_state(data_dir=data_dir, env=env)

    logger.info(
        "[market_stability_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f",
        env,
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    out_file = data_dir / "analysis" / "market_stability_engine_pro.json"
    save_json_file(out_file, state)
    logger.info(
        "[market_stability_engine_pro] market_stability_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    try:
        publish_event(
            "market.stability.state",
            "market_stability_engine_pro",
            severity=severity,
            payload=state,
        )
        logger.info(
            "[market_stability_engine_pro] Event market.stability.state publié "
            "(severity=%s, score=%.2f)",
            severity,
            state.get("score"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[market_stability_engine_pro] Impossible de publier l'event "
            "market.stability.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
