# src/v2/analysis/cross_asset_liquidity_engine_pro.py

"""
Cross-Asset Liquidity Engine PRO

Objectif :
- Agréger les signaux de liquidité sur plusieurs poches (crypto, actions, obligations, macro)
- Produire un score 0–100 + un régime (risk_on / risk_off / transition / unknown)
- Exposer un état global dans data/analysis/cross_asset_liquidity_engine_pro.json
- Publier un event "liquidity.cross_asset.state" dans l'event bus

Le moteur est TOLÉRANT à l'absence de données : il tombe sur un mode neutre/caution (score ~50).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timezone

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event

logger = get_logger("cross_asset_liquidity_engine_pro")

# -----------------------------------------------------------------------------
# Dataclasses
# -----------------------------------------------------------------------------
@dataclass
class ComponentLiquidityState:
    score: float
    flag: str
    regime: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class CrossAssetLiquidityState:
    timestamp: str
    env: str
    regime: str
    global_flag: str
    score: float
    components: Dict[str, Dict[str, Any]]
    reasons: List[str]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _now_utc_iso() -> str:
    """Retourne un timestamp ISO8601 en UTC (suffixe Z)."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _extract_component_state(
    data: Dict[str, Any],
    default_score: float = 50.0,
    default_flag: str = "neutral",
) -> ComponentLiquidityState:
    """
    Extrait un état de liquidité d'un sous-moteur standardisé NSC
    (liquidity_engine_pro, equity_liquidity_engine_pro, etc.)
    """
    if not data:
        return ComponentLiquidityState(
            score=default_score,
            flag=default_flag,
            regime="unknown",
            details=None,
        )

    score = float(data.get("score", default_score))
    flag = str(data.get("global_flag") or data.get("flag") or default_flag)
    regime = str(data.get("regime") or "unknown")

    details = {
        "score": score,
        "flag": flag,
        "regime": regime,
    }
    # Ajoute quelques métriques si disponibles
    for key in ("liquidity_score", "stress_score", "nb_assets", "avg_spread_bps"):
        if key in data:
            details[key] = data[key]

    return ComponentLiquidityState(
        score=score,
        flag=flag,
        regime=regime,
        details=details,
    )


def _extract_macro_liquidity_state(
    data: Dict[str, Any],
    default_score: float = 50.0,
    default_flag: str = "neutral",
) -> ComponentLiquidityState:
    """
    Extrait l'état macro de liquidité globale.
    Format attendu (exemple) :
    {
      "score": 62.5,
      "regime": "liquidity_on",
      "flag": "supportive",
      "metrics": {...}
    }
    """
    if not data:
        return ComponentLiquidityState(
            score=default_score,
            flag=default_flag,
            regime="unknown",
            details=None,
        )

    score = float(data.get("score", default_score))
    flag = str(data.get("flag") or data.get("global_flag") or default_flag)
    regime = str(data.get("regime") or "unknown")

    details = {
        "score": score,
        "flag": flag,
        "regime": regime,
    }
    if "metrics" in data and isinstance(data["metrics"], dict):
        details["metrics"] = data["metrics"]

    return ComponentLiquidityState(
        score=score,
        flag=flag,
        regime=regime,
        details=details,
    )


def _compute_cross_asset_score(
    components: Dict[str, ComponentLiquidityState]
) -> float:
    """
    Combine les scores des différentes poches via une moyenne pondérée simple.
    Pour l’instant :
      - crypto : 35%
      - equities : 35%
      - bonds : 20%
      - macro : 10%
    Les composants manquants gardent le score par défaut (~50).
    """
    weights = {
        "crypto": 0.35,
        "equities": 0.35,
        "bonds": 0.20,
        "macro": 0.10,
    }

    total = 0.0
    for name, comp in components.items():
        w = weights.get(name, 0.0)
        total += w * comp.score

    return round(total, 2)


def _derive_global_flag_and_regime(
    composite_score: float, components: Dict[str, ComponentLiquidityState]
) -> Tuple[str, str, List[str]]:
    """
    Déduit un flag global + régime (risk_on / risk_off / transition / unknown)
    à partir du score agrégé et des flags composants.
    """
    reasons: List[str] = []
    comp_flags = {name: c.flag for name, c in components.items()}
    comp_regimes = {name: c.regime for name, c in components.items()}

    any_stress = any(
        f in {"stress", "crisis", "panic"} for f in comp_flags.values()
    )
    all_supportive = all(
        f in {"ok", "supportive"} for f in comp_flags.values()
    )

    macro_regime = comp_regimes.get("macro", "unknown")

    # Détermination du flag global
    if composite_score >= 70 and all_supportive:
        global_flag = "supportive"
        reasons.append(
            "Score de liquidité agrégé élevé (>= 70) avec des poches globalement supportives."
        )
    elif composite_score <= 40 or any_stress:
        global_flag = "stress"
        if composite_score <= 40:
            reasons.append("Score de liquidité agrégé faible (<= 40).")
        if any_stress:
            reasons.append(
                "Au moins une poche de liquidité est en mode stress/crisis."
            )
    else:
        global_flag = "neutral"
        reasons.append(
            "Score de liquidité agrégé intermédiaire – environnement neutre / mitigé."
        )

    # Détermination du régime
    if composite_score >= 65 and macro_regime in {"liquidity_on", "expansion"}:
        regime = "risk_on"
        reasons.append(
            "Régime macro de liquidité ON/expansion et score agrégé >= 65 (risk_on)."
        )
    elif composite_score <= 45 or global_flag == "stress":
        regime = "risk_off"
        reasons.append(
            "Risque de liquidité élevé ou flag global en stress (risk_off)."
        )
    elif 45 < composite_score < 65:
        regime = "transition"
        reasons.append(
            "Zone de transition (score intermédiaire entre 45 et 65)."
        )
    else:
        regime = "unknown"
        reasons.append("Régime de liquidité global indéterminé (unknown).")

    return global_flag, regime, reasons


def _choose_severity(global_flag: str, regime: str) -> str:
    """
    Mappe le flag/régime vers une sévérité d'event.
    """
    if regime == "risk_off" and global_flag == "stress":
        return "critical"
    if regime in {"transition", "unknown"} or global_flag in {"neutral", "caution"}:
        return "warning"
    return "info"


# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
def build_cross_asset_liquidity_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Lit les différentes sources de liquidité et construit l'état cross-asset.
    Retourne (state_dict, severity).
    """
    analysis_dir = data_dir / "analysis"
    macro_dir = data_dir / "macro"

    # Fichiers d'entrée
    crypto_file = analysis_dir / "liquidity_engine_pro.json"
    equities_file = analysis_dir / "equity_liquidity_engine_pro.json"
    bonds_file = analysis_dir / "bond_liquidity_engine_pro.json"
    macro_file = macro_dir / "global_liquidity_pulse.json"

    # Chargement tolérant aux erreurs / fichiers manquants
    crypto_raw = load_json_file(crypto_file, default={})
    equities_raw = load_json_file(equities_file, default={})
    bonds_raw = load_json_file(bonds_file, default={})
    macro_raw = load_json_file(macro_file, default={})

    components: Dict[str, ComponentLiquidityState] = {
        "crypto": _extract_component_state(crypto_raw),
        "equities": _extract_component_state(equities_raw),
        "bonds": _extract_component_state(bonds_raw),
        "macro": _extract_macro_liquidity_state(macro_raw),
    }

    composite_score = _compute_cross_asset_score(components)
    global_flag, regime, reasons = _derive_global_flag_and_regime(
        composite_score, components
    )

    # Cas où toutes les sources sont vides -> on ajoute une raison explicite
    if not any([crypto_raw, equities_raw, bonds_raw, macro_raw]):
        reasons.append(
            "Aucune source de liquidité spécifique disponible – utilisation d'un score neutre par défaut."
        )

    state = CrossAssetLiquidityState(
        timestamp=_now_utc_iso(),
        env=env,
        regime=regime,
        global_flag=global_flag,
        score=composite_score,
        components={
            name: (comp.details or {"score": comp.score, "flag": comp.flag, "regime": comp.regime})
            for name, comp in components.items()
        },
        reasons=reasons,
    )

    severity = _choose_severity(global_flag, regime)
    return asdict(state), severity


def main() -> None:
    """
    Entrypoint CLI :
      python -m src.v2.analysis.cross_asset_liquidity_engine_pro
    """
    data_dir = Path(os.getenv("NSC_DATA_DIR", "data")).resolve()
    env = os.getenv("NSC_ENV", "PREPROD")

    logger.info(
        "[cross_asset_liquidity_engine_pro] DATA_DIR=%s, env=%s",
        str(data_dir),
        env,
    )

    state, severity = build_cross_asset_liquidity_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "cross_asset_liquidity_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[cross_asset_liquidity_engine_pro] cross_asset_liquidity_engine_pro.json "
        "sauvegardé (regime=%s, global_flag=%s, score=%.2f)",
        state["regime"],
        state["global_flag"],
        state["score"],
    )

    # Publication event
    try:
        publish_event(
            event_type="liquidity.cross_asset.state",
            source="cross_asset_liquidity_engine_pro",
            payload=state,
            severity=severity,
        )
        logger.info(
            "[cross_asset_liquidity_engine_pro] Event liquidity.cross_asset.state publié (severity=%s, regime=%s, score=%.2f)",
            severity,
            state["regime"],
            state["score"],
        )
    except Exception as e:  # pragma: no cover - robustesse runtime
        logger.error(
            "[cross_asset_liquidity_engine_pro] Impossible de publier l'event liquidity.cross_asset.state : %s",
            e,
        )


if __name__ == "__main__":
    main()
