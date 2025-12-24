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
class InformationImbalanceMetrics:
    """
    Métriques de déséquilibre informationnel / prix.

    JSON attendu dans data/analysis/information_imbalance.json (format souple) :

    {
      "price_leads_score": 0.6,             # 0–1 (prix qui leadent l'info)
      "info_leads_score": 0.7,              # 0–1 (news/flow qui leadent le prix)
      "divergence_score": 0.5,              # 0–1 (prix vs sentiment / flow)
      "hidden_flow_score": 0.4,             # 0–1 (signaux "cachés" / dark)
      "nb_assets": 120,                     # nb d'actifs analysés
      "share_conflicting_signals": 0.3      # part d'actifs en forte divergence
    }
    """

    price_leads_score: Optional[float]
    info_leads_score: Optional[float]
    divergence_score: Optional[float]
    hidden_flow_score: Optional[float]
    nb_assets: Optional[int]
    share_conflicting_signals: Optional[float]


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


def load_information_imbalance_metrics(raw: Any) -> InformationImbalanceMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return InformationImbalanceMetrics(
        price_leads_score=_get_float(raw.get("price_leads_score")),
        info_leads_score=_get_float(raw.get("info_leads_score")),
        divergence_score=_get_float(raw.get("divergence_score")),
        hidden_flow_score=_get_float(raw.get("hidden_flow_score")),
        nb_assets=_get_int(raw.get("nb_assets")),
        share_conflicting_signals=_get_float(raw.get("share_conflicting_signals")),
    )


# ---------------------------------------------------------------------------
# Logic Information Imbalance
# ---------------------------------------------------------------------------

def infer_information_imbalance_regime_and_score(
    m: InformationImbalanceMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime d'information imbalance + flag global + score NSC.

    Intuition :
    - Scores élevés + part importante de signaux contradictoires → "information_imbalance_high"
      → mode défensif / risk_off.
    - Scores moyens → "information_imbalance_watch" → prudence (caution).
    - Scores bas / structure cohérente → "balanced" → supportive.

    Le score NSC est dans l'espace 0–100 (50 = neutre).
    """

    reasons: List[str] = []

    values = [
        v
        for v in (
            m.price_leads_score,
            m.info_leads_score,
            m.divergence_score,
            m.hidden_flow_score,
        )
        if v is not None
    ]
    if not values:
        reasons.append(
            "Aucune donnée d'information imbalance exploitable – score neutre."
        )
        return "unknown", "caution", 50.0, reasons

    # Seuils
    HIGH = 0.65
    MID = 0.40
    HIGH_CONFLICT = 0.40  # ≥ 40% d'actifs en conflit = lourd
    MID_CONFLICT = 0.25

    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    price_leads = m.price_leads_score
    info_leads = m.info_leads_score
    div = m.divergence_score
    hidden = m.hidden_flow_score
    nb_assets = m.nb_assets
    share_conf = m.share_conflicting_signals

    # Mesure globale pour info / prix
    avg_core = sum(values) / len(values)

    # 1) Fort déséquilibre informationnel → risk_off
    if (
        avg_core >= HIGH
        or (div is not None and div >= HIGH)
        or (hidden is not None and hidden >= HIGH)
        or (share_conf is not None and share_conf >= HIGH_CONFLICT)
    ):
        regime = "information_imbalance_high"
        global_flag = "risk_off"
        # Score un peu sous neutre pour refléter le danger,
        # mais pas très bas car ce n'est qu'un bloc du meta-score global.
        score = 42.0

        msg = (
            "INFORMATION IMBALANCE – HIGH : forte asymétrie entre information et prix, "
            "avec risque accru de moves violents ou de piégeage."
        )
        parts = []
        parts.append(f"avg_core={avg_core:.2f}")
        if div is not None:
            parts.append(f"divergence_score={div:.2f}")
        if hidden is not None:
            parts.append(f"hidden_flow_score={hidden:.2f}")
        if share_conf is not None:
            parts.append(f"share_conflicting_signals={share_conf:.2f}")
        if nb_assets is not None:
            parts.append(f"nb_assets={nb_assets}")
        if parts:
            msg += " " + ", ".join(parts)
        reasons.append(msg)

    # 2) Déséquilibre modéré / sous surveillance
    elif (
        avg_core >= MID
        or (share_conf is not None and share_conf >= MID_CONFLICT)
    ):
        regime = "information_imbalance_watch"
        global_flag = "caution"
        score = 47.0

        msg = (
            "INFORMATION IMBALANCE – WATCH : signaux d'asymétrie informationnelle "
            "présents, mais sans rupture extrême."
        )
        parts = []
        parts.append(f"avg_core={avg_core:.2f}")
        if share_conf is not None:
            parts.append(f"share_conflicting_signals={share_conf:.2f}")
        if nb_assets is not None:
            parts.append(f"nb_assets={nb_assets}")
        if parts:
            msg += " " + ", ".join(parts)
        reasons.append(msg)

    # 3) Structure équilibrée / pas de déséquilibre marqué
    else:
        regime = "balanced"
        global_flag = "supportive"
        score = 60.0

        msg = (
            "INFORMATION IMBALANCE – BALANCED : cohérence globale entre prix, flux et "
            "information – pas de déséquilibre majeur détecté."
        )
        parts = []
        parts.append(f"avg_core={avg_core:.2f}")
        if nb_assets is not None:
            parts.append(f"nb_assets={nb_assets}")
        if parts:
            msg += " " + ", ".join(parts)
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


def build_information_imbalance_state(
    data_dir: Path,
    env: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de Information Imbalance à partir de :

    data/analysis/information_imbalance.json
    """

    src_file = data_dir / "analysis" / "information_imbalance.json"
    raw = load_json_file(src_file, default={})

    metrics = load_information_imbalance_metrics(raw)
    regime, global_flag, score, reasons = infer_information_imbalance_regime_and_score(
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
            "price_leads_score": metrics.price_leads_score,
            "info_leads_score": metrics.info_leads_score,
            "divergence_score": metrics.divergence_score,
            "hidden_flow_score": metrics.hidden_flow_score,
            "nb_assets": metrics.nb_assets,
            "share_conflicting_signals": metrics.share_conflicting_signals,
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
        "[information_imbalance_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_information_imbalance_state(data_dir=data_dir, env=env)

    logger.info(
        "[information_imbalance_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f",
        env,
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    out_file = data_dir / "analysis" / "information_imbalance_engine_pro.json"
    save_json_file(out_file, state)
    logger.info(
        "[information_imbalance_engine_pro] information_imbalance_engine_pro.json "
        "sauvegardé (regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    try:
        publish_event(
            "information.imbalance.state",
            "information_imbalance_engine_pro",
            severity=severity,
            payload=state,
        )
        logger.info(
            "[information_imbalance_engine_pro] Event information.imbalance.state publié "
            "(severity=%s, score=%.2f)",
            severity,
            state.get("score"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[information_imbalance_engine_pro] Impossible de publier l'event "
            "information.imbalance.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
