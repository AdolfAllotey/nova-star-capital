#!/usr/bin/env python
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("cross_asset_engine_pro")


def _get_root_and_data_dir() -> tuple[Path, Path]:
    """
    Détermine ROOT_DIR et DATA_DIR en respectant la convention NSC :
    - NSC_ROOT_DIR / NSC_DATA_DIR si présents
    - sinon, on remonte depuis ce fichier.
    """
    root_env = os.getenv("NSC_ROOT_DIR")
    data_env = os.getenv("NSC_DATA_DIR")

    if root_env:
        root_dir = Path(root_env).resolve()
    else:
        # src/v2/analysis/cross_asset_engine_pro.py → remonter 3 niveaux → /opt/nsc/app
        root_dir = Path(__file__).resolve().parents[3]

    if data_env:
        data_dir = Path(data_env).resolve()
    else:
        data_dir = root_dir / "data"

    return root_dir, data_dir


def _load_market_overview(data_dir: Path) -> Dict[str, Any]:
    """Charge market_overview.json si présent, sinon renvoie un défaut neutre."""
    path = data_dir / "market" / "market_overview.json"
    default = {
        "regime": "neutral",
        "meta_score_nsc": 50.0,
        "pivot": "bitcoin",
        "inputs": {},
    }
    return load_json_file(path, default=default)


def _compute_risk_from_regime(regime: str, meta_score: float) -> Dict[str, Any]:
    """
    Traduit le régime de marché + meta_score NSC en score de risque cross-asset.
    On reste volontairement simple (crypto-centré) mais extensible.
    """
    regime = (regime or "neutral").lower()

    # Base selon le régime
    if regime in ("bull", "risk_on"):
        base = 75.0
    elif regime in ("bear", "risk_off", "panic"):
        base = 30.0
    elif regime in ("caution", "choppy"):
        base = 50.0
    else:
        base = 55.0  # neutre / inconnu

    # Ajustement par le meta_score global NSC (50 = neutre)
    # Petit poids pour éviter d'exagérer
    adj = (meta_score - 50.0) * 0.30
    risk_score = max(0.0, min(100.0, base + adj))

    # Traduction en "risk regime" simple
    if risk_score >= 70.0:
        risk_regime = "risk_on"
    elif risk_score >= 45.0:
        risk_regime = "balanced"
    else:
        risk_regime = "risk_off"

    # Flag global pour la console de risque
    if risk_score >= 65.0:
        global_flag = "ok"
    elif risk_score >= 45.0:
        global_flag = "caution"
    else:
        global_flag = "danger"

    return {
        "risk_score": risk_score,
        "risk_regime": risk_regime,
        "global_flag": global_flag,
    }


def compute_cross_asset_overview() -> Dict[str, Any]:
    """
    Engine principal Cross-Asset Pro :
    - lit market_overview.json
    - calcule un score de risque cross-asset
    - exporte un JSON compatible avec les autres *Engine Pro* (stats + assets).
    """
    root_dir, data_dir = _get_root_and_data_dir()
    logger.info("[cross_asset_engine_pro] ROOT_DIR=%s, DATA_DIR=%s", root_dir, data_dir)

    market = _load_market_overview(data_dir)
    regime = market.get("regime", "neutral")
    meta_score = float(market.get("meta_score_nsc", 50.0))

    risk_info = _compute_risk_from_regime(regime, meta_score)

    # On modélise un seul "asset_class" synthétique pour l'instant : crypto_risk
    asset_entry: Dict[str, Any] = {
        "asset_class": "crypto_risk",
        "risk_score": risk_info["risk_score"],
        "risk_regime": risk_info["risk_regime"],
        "inputs": {
            "market_regime": regime,
            "meta_score_nsc": meta_score,
        },
        "reasons": _build_reasons(risk_info, regime, meta_score),
    }

    assets: List[Dict[str, Any]] = [asset_entry]

    stats: Dict[str, Any] = {
        "nb_assets": len(assets),
        "risk_regime": risk_info["risk_regime"],
        "avg_risk_score": risk_info["risk_score"],
        "global_flag": risk_info["global_flag"],
    }

    overview: Dict[str, Any] = {
        "stats": stats,
        "assets": assets,
    }

    logger.info(
        "[cross_asset_engine_pro] Cross-asset évalué: regime=%s, risk_score=%.2f, flag=%s",
        risk_info["risk_regime"],
        risk_info["risk_score"],
        risk_info["global_flag"],
    )
    return overview


def _build_reasons(
    risk_info: Dict[str, Any],
    regime: str,
    meta_score: float,
) -> List[str]:
    reasons: List[str] = []
    risk_regime = risk_info["risk_regime"]
    risk_score = risk_info["risk_score"]

    reasons.append(f"Régime marché: {regime} (meta_score_nsc≈{meta_score:.1f})")

    if risk_regime == "risk_on":
        reasons.append("Contexte plutôt favorable (risk_on)")
    elif risk_regime == "balanced":
        reasons.append("Contexte équilibré (balanced)")
    else:
        reasons.append("Contexte prudent / risk_off")

    if risk_score < 40:
        reasons.append("Score de risque cross-asset faible (<40)")
    elif risk_score > 70:
        reasons.append("Score de risque cross-asset élevé (>70)")

    return reasons


def main() -> None:
    root_dir, data_dir = _get_root_and_data_dir()
    overview = compute_cross_asset_overview()

    out_path = data_dir / "analysis" / "cross_asset_engine_pro.json"
    save_json_file(out_path, overview)
    logger.info(
        "[cross_asset_engine_pro] cross_asset_engine_pro.json sauvegardé (%s, nb_assets=%d).",
        out_path,
        len(overview.get("assets", [])),
    )


if __name__ == "__main__":
    main()
