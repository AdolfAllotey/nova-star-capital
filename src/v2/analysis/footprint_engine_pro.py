"""
Footprint Engine PRO – analyse du footprint microstructure (delta, agressivité, absorption, exhaustion).

Ce module lit un fichier JSON de footprints (ex: data/market/footprint_bars.json)
et produit un état agrégé dans:
    data/analysis/footprint_engine_pro.json

Il publie également un event dans le message bus:
    type = "microstructure.footprint.state"
    source = "footprint_engine_pro"
"""

from __future__ import annotations

import os
import logging
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event


# ---------------------------------------------------------------------------
# Logging basique (sans src.v2.logger)
# ---------------------------------------------------------------------------

logger = logging.getLogger("footprint_engine_pro")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_env() -> str:
    """Retourne l'environnement NSC (ex: PREPROD, PROD)."""
    return os.getenv("NSC_ENV", "PREPROD")


def get_data_dir() -> Path:
    """
    Retourne le répertoire DATA principal.

    On s'aligne sur les autres modules:
    - variable d'env NSC_DATA_DIR prioritaire
    - sinon "data" relatif au projet
    """
    base = os.getenv("NSC_DATA_DIR", "data")
    data_dir = Path(base).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Chargement des footprints
# ---------------------------------------------------------------------------

def load_footprint_bars(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Charge les footprints depuis data/market/footprint_bars.json.

    Format attendu (liste de barres):
    [
      {
        "timestamp": "...",
        "delta": float,                # volume acheteur - volume vendeur
        "buy_volume": float,
        "sell_volume": float,
        "total_volume": float,
        "max_bid_volume": float,
        "max_ask_volume": float,
        "footprint_type": "normal|absorption|exhaustion|imbalance",
        ...
      },
      ...
    ]
    """
    footprint_path = data_dir / "market" / "footprint_bars.json"
    bars = load_json_file(footprint_path, default=[])
    if not isinstance(bars, list):
        logger.warning(
            "[footprint_engine_pro] Format inattendu pour %s (type=%s), "
            "on retourne une liste vide.",
            footprint_path,
            type(bars),
        )
        return []
    return bars


# ---------------------------------------------------------------------------
# Analyse footprint
# ---------------------------------------------------------------------------

def analyse_footprint_bars(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyse les footprints et retourne un état :
    - global_flag: "ok" / "caution" / "danger"
    - regime: "aggressive_buy" / "aggressive_sell" / "balanced" / "choppy" / "unknown"
    - score: float 0–100
    - metrics: dict de métriques agrégées
    - reasons: liste de raisons textuelles
    """

    if not bars:
        return {
            "symbol": "global",
            "regime": "unknown",
            "global_flag": "caution",
            "score": 50.0,
            "metrics": {
                "nb_bars": 0,
                "avg_delta": None,
                "max_abs_delta": None,
                "buy_dominance_ratio": None,
                "nb_absorption_bars": 0,
                "nb_exhaustion_bars": 0,
                "nb_imbalance_bars": 0,
            },
            "reasons": [
                "Aucun footprint disponible (fichier footprint_bars.json vide ou introuvable)."
            ],
        }

    nb_bars = len(bars)

    deltas: List[float] = []
    nb_buy_bars = 0
    nb_sell_bars = 0
    nb_absorption_bars = 0
    nb_exhaustion_bars = 0
    nb_imbalance_bars = 0

    for b in bars:
        delta = safe_float(b.get("delta"))
        if delta is not None:
            deltas.append(delta)
            if delta > 0:
                nb_buy_bars += 1
            elif delta < 0:
                nb_sell_bars += 1

        ftype = (b.get("footprint_type") or "").lower()
        if ftype == "absorption":
            nb_absorption_bars += 1
        elif ftype == "exhaustion":
            nb_exhaustion_bars += 1
        elif ftype == "imbalance":
            nb_imbalance_bars += 1

    avg_delta = sum(deltas) / len(deltas) if deltas else None
    max_abs_delta = max((abs(d) for d in deltas), default=None) if deltas else None

    if nb_bars > 0:
        buy_dominance_ratio = nb_buy_bars / nb_bars
    else:
        buy_dominance_ratio = None

    reasons: List[str] = []

    # Détermination du régime
    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    if buy_dominance_ratio is None or avg_delta is None:
        reasons.append("Deltas footprint insuffisants pour un diagnostic clair.")
        regime = "unknown"
        global_flag = "caution"
        score = 50.0
    else:
        # Exemple de règles simples
        if buy_dominance_ratio >= 0.65 and avg_delta > 0:
            regime = "aggressive_buy"
            global_flag = "ok"
            score = 70.0
            reasons.append(
                "Flux acheteur agressif (ratio de barres acheteuses élevé, delta moyen positif)."
            )
        elif buy_dominance_ratio <= 0.35 and avg_delta < 0:
            regime = "aggressive_sell"
            global_flag = "danger"
            score = 35.0
            reasons.append(
                "Flux vendeur agressif (ratio de barres vendeuses élevé, delta moyen négatif)."
            )
        else:
            regime = "balanced"
            global_flag = "ok"
            score = 60.0
            reasons.append(
                "Footprint globalement équilibré (flux acheteurs / vendeurs relativement symétrique)."
            )

        # Ajustement en fonction des signaux d’absorption / exhaustion / imbalance
        if nb_absorption_bars > 0:
            reasons.append(
                f"{nb_absorption_bars} barres d'absorption détectées (gros volume absorbant)."
            )
            # absorption => potentiel blocage/retournement
            score -= 5.0

        if nb_exhaustion_bars > 0:
            reasons.append(
                f"{nb_exhaustion_bars} barres d'exhaustion détectées (fatigue des acheteurs/vendeurs)."
            )
            # exhaustion => fin de mouvement en cours
            score -= 5.0

        if nb_imbalance_bars > 0:
            reasons.append(
                f"{nb_imbalance_bars} barres avec déséquilibre fort (stacked imbalance)."
            )
            score -= 5.0

        # On borne le score
        score = max(0.0, min(100.0, score))

        # Ajuste le global_flag en fonction du score final
        if score >= 65:
            global_flag = "ok"
        elif score >= 45:
            global_flag = "caution"
        else:
            global_flag = "danger"

    metrics = {
        "nb_bars": nb_bars,
        "avg_delta": avg_delta,
        "max_abs_delta": max_abs_delta,
        "buy_dominance_ratio": buy_dominance_ratio,
        "nb_absorption_bars": nb_absorption_bars,
        "nb_exhaustion_bars": nb_exhaustion_bars,
        "nb_imbalance_bars": nb_imbalance_bars,
    }

    return {
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": round(score, 2),
        "metrics": metrics,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    env = get_env()
    data_dir = get_data_dir()
    analysis_dir = data_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "[footprint_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    # 1) Charger les footprints
    bars = load_footprint_bars(data_dir)

    # 2) Analyse
    state_core = analyse_footprint_bars(bars)

    # 3) Enrichir avec timestamp & env
    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    state = {
        "timestamp": now_ts,
        "env": env,
        **state_core,
    }

    # 4) Sauvegarde JSON
    out_path = analysis_dir / "footprint_engine_pro.json"
    save_json_file(out_path, state)
    logger.info(
        "[footprint_engine_pro] footprint_engine_pro.json sauvegardé "
        "(regime=%s, flag=%s, score=%.2f)",
        state["regime"],
        state["global_flag"],
        state["score"],
    )

    # 5) Publication dans le message bus
    severity = "info"
    if state["global_flag"] == "caution":
        severity = "warning"
    elif state["global_flag"] == "danger":
        severity = "critical"

    try:
        publish_event(
            event_type="microstructure.footprint.state",
            source="footprint_engine_pro",
            payload=state,
            severity=severity,
        )
        logger.info(
            "[footprint_engine_pro] Event microstructure.footprint.state publié "
            "(severity=%s, regime=%s, score=%.2f)",
            severity,
            state["regime"],
            state["score"],
        )
    except Exception as exc:  # garde-fou
        logger.error(
            "[footprint_engine_pro] Impossible de publier l'event microstructure.footprint.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
