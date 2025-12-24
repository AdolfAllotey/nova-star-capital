"""
Sector Engine Pro (Saison 2 – NSC)

Objectif :
- Analyser la rotation sectorielle (momentum, cycle, liquidité)
- Produire un sector_flag par secteur (ok / soft_veto / hard_veto)
- Fournir un global_flag pour la risk console & le meta-score

Entrées principales :
- data/analysis/momentum_engine_4_0.json
- data/analysis/cycle_engine_pro.json (optionnel)
- data/analysis/liquidity_engine_pro.json (optionnel)
- data/meta/asset_sectors.json (optionnel, mapping symbol -> secteur)

Sortie :
- data/analysis/sector_engine_pro.json
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from pathlib import Path

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger("sector_engine_pro")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SectorMetrics:
    symbol: str
    sector: str
    momentum_score: float
    meta_score: float
    cycle_phase: Optional[str] = None
    cycle_phase_score: Optional[float] = None
    liquidity_score: Optional[float] = None


# ---------------------------------------------------------------------------
# Helpers pour charger les inputs
# ---------------------------------------------------------------------------


def _load_momentum_assets(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Charge les assets depuis momentum_engine_4_0.json.
    Fallback : [] si absent ou structure inattendue.
    """
    path = data_dir / "analysis" / "momentum_engine_4_0.json"
    data = load_json_file(path, default={})
    assets = data.get("assets") if isinstance(data, dict) else None
    if not isinstance(assets, list):
        assets = []
    return assets


def _load_cycle_assets(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Charge les infos de cycle depuis cycle_engine_pro.json et indexe par symbol.
    """
    path = data_dir / "analysis" / "cycle_engine_pro.json"
    data = load_json_file(path, default={})
    assets = data.get("assets") if isinstance(data, dict) else None
    if not isinstance(assets, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for a in assets:
        sym = a.get("symbol")
        if sym:
            out[sym] = a
    return out


def _load_liquidity_assets(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Charge les infos de liquidité depuis liquidity_engine_pro.json et indexe par symbol.
    """
    path = data_dir / "analysis" / "liquidity_engine_pro.json"
    data = load_json_file(path, default={})
    assets = data.get("assets") if isinstance(data, dict) else None
    if not isinstance(assets, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for a in assets:
        sym = a.get("symbol")
        if sym:
            out[sym] = a
    return out


def _load_sector_map(data_dir: Path) -> Dict[str, str]:
    """
    Charge le mapping symbol -> secteur depuis data/meta/asset_sectors.json.

    Formats supportés :
    1) { "bitcoin": "layer1", "ethereum": "layer1" }
    2) [ {"symbol": "bitcoin", "sector": "layer1"}, ... ]

    Si rien n'est trouvé, on retournera un dict vide et on
    utilisera 'other' comme secteur par défaut.
    """
    path = data_dir / "meta" / "asset_sectors.json"
    raw = load_json_file(path, default={})

    mapping: Dict[str, str] = {}

    if isinstance(raw, dict):
        # Mapping direct symbol -> secteur
        for sym, sec in raw.items():
            if isinstance(sym, str) and isinstance(sec, str):
                mapping[sym.lower()] = sec
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol")
            sec = item.get("sector")
            if isinstance(sym, str) and isinstance(sec, str):
                mapping[sym.lower()] = sec

    if mapping:
        logger.info(
            "[sector_engine_pro] Mapping secteurs chargé depuis %s (n=%d).",
            path,
            len(mapping),
        )
    else:
        logger.info(
            "[sector_engine_pro] Aucun mapping secteurs explicite trouvé (%s), "
            "utilisation du secteur 'other' par défaut.",
            path,
        )
    return mapping


# ---------------------------------------------------------------------------
# Classification sectorielle
# ---------------------------------------------------------------------------


def _classify_sector(
    momentum_values: List[float],
    cycle_scores: List[float],
    liquidity_scores: List[float],
) -> Dict[str, Any]:
    """
    Classe la rotation sectorielle + risk_regime + sector_flag.
    """
    if momentum_values:
        avg_momentum = statistics.mean(momentum_values)
    else:
        avg_momentum = 0.0

    if cycle_scores:
        avg_cycle = statistics.mean(cycle_scores)
    else:
        avg_cycle = 0.0

    if liquidity_scores:
        avg_liquidity = statistics.mean(liquidity_scores)
    else:
        avg_liquidity = 0.0

    # Rotation state (type Leadership / Improving / Lagging / Weakening)
    if avg_momentum >= 70 and avg_cycle >= 55:
        rotation_state = "leadership"
    elif avg_momentum >= 60:
        rotation_state = "improving"
    elif avg_momentum >= 45:
        rotation_state = "lagging"
    else:
        rotation_state = "weakening"

    # Risk regime & flags
    risk_regime = "neutral"
    sector_flag = "ok"
    reasons: List[str] = []

    # Cas très négatif : mauvais momentum + mauvais cycle + liquidité faible
    if avg_momentum < 40 and avg_cycle < 40 and avg_liquidity < 50:
        risk_regime = "avoid"
        sector_flag = "hard_veto"
        reasons.append("Momentum faible + cycle défavorable + liquidité faible")
    # Cas prudent : momentum moyen / cycle fragile
    elif avg_momentum < 50 or avg_cycle < 45:
        risk_regime = "risk_off"
        sector_flag = "soft_veto"
        if avg_momentum < 50:
            reasons.append("Momentum sectoriel sous 50")
        if avg_cycle < 45:
            reasons.append("Cycle sectoriel prudent (<45)")
    # Cas pro-risk : momentum + cycle solides et liquidité correcte
    elif avg_momentum >= 65 and avg_cycle >= 55 and avg_liquidity >= 60:
        risk_regime = "pro_risk"
        sector_flag = "ok"
        reasons.append("Secteur en leadership (momentum + cycle + liquidité)")

    # Si aucune raison explicite, on met un message par défaut
    if not reasons:
        reasons.append("Configuration sectorielle neutre / standard")

    return {
        "avg_momentum": avg_momentum,
        "avg_cycle": avg_cycle,
        "avg_liquidity": avg_liquidity,
        "rotation_state": rotation_state,
        "risk_regime": risk_regime,
        "sector_flag": sector_flag,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def compute_sector_engine(data_dir: Path) -> Dict[str, Any]:
    """
    Calcule Sector Engine Pro à partir des différents modules pro.
    """
    # 1) Charger les entrées
    momentum_assets = _load_momentum_assets(data_dir)
    cycle_by_symbol = _load_cycle_assets(data_dir)
    liquidity_by_symbol = _load_liquidity_assets(data_dir)
    sector_map = _load_sector_map(data_dir)

    if not momentum_assets:
        logger.warning(
            "[sector_engine_pro] Aucun asset trouvé dans momentum_engine_4_0.json, "
            "retour d'un résultat vide."
        )
        return {
            "timestamp": None,
            "sectors": {},
            "stats": {
                "nb_sectors": 0,
                "nb_soft_veto": 0,
                "nb_hard_veto": 0,
                "global_flag": "unknown",
            },
        }

    # 2) Construire les metrics par asset
    by_sector_assets: Dict[str, List[SectorMetrics]] = {}

    for asset in momentum_assets:
        symbol = asset.get("symbol")
        if not symbol:
            continue

        sym_lower = str(symbol).lower()
        sector = sector_map.get(sym_lower, "other")

        meta_score = float(asset.get("meta_score", 0.0))
        momentum_score = float(asset.get("momentum_score", 0.0))

        # Cycle
        cycle_info = cycle_by_symbol.get(symbol, {})
        cycle_phase = cycle_info.get("cycle_phase")
        cycle_phase_score = cycle_info.get("cycle_phase_score")

        # Liquidité
        liq_info = liquidity_by_symbol.get(symbol, {})
        liquidity_score = liq_info.get("liquidity_score")

        metrics = SectorMetrics(
            symbol=symbol,
            sector=sector,
            momentum_score=momentum_score,
            meta_score=meta_score,
            cycle_phase=cycle_phase,
            cycle_phase_score=cycle_phase_score,
            liquidity_score=liquidity_score,
        )

        by_sector_assets.setdefault(sector, []).append(metrics)

    # 3) Agrégation par secteur
    sectors_out: Dict[str, Any] = {}
    nb_soft_veto = 0
    nb_hard_veto = 0

    for sector, assets in by_sector_assets.items():
        momentum_values = [a.momentum_score for a in assets]
        cycle_scores = [
            a.cycle_phase_score for a in assets if a.cycle_phase_score is not None
        ]
        liquidity_scores = [
            a.liquidity_score for a in assets if a.liquidity_score is not None
        ]

        classification = _classify_sector(
            momentum_values=momentum_values,
            cycle_scores=cycle_scores,
            liquidity_scores=liquidity_scores,
        )

        if classification["sector_flag"] == "soft_veto":
            nb_soft_veto += 1
        elif classification["sector_flag"] == "hard_veto":
            nb_hard_veto += 1

        sectors_out[sector] = {
            "momentum": classification["avg_momentum"],
            "cycle_score": classification["avg_cycle"],
            "liquidity_score": classification["avg_liquidity"],
            "rotation_state": classification["rotation_state"],
            "risk_regime": classification["risk_regime"],
            "sector_flag": classification["sector_flag"],
            "nb_assets": len(assets),
            "reasons": classification["reasons"],
        }

    # 4) Global flag
    if nb_hard_veto > 0:
        global_flag = "danger"
    elif nb_soft_veto > 0:
        global_flag = "caution"
    else:
        global_flag = "ok"

    overview = {
        "sectors": sectors_out,
        "stats": {
            "nb_sectors": len(sectors_out),
            "nb_soft_veto": nb_soft_veto,
            "nb_hard_veto": nb_hard_veto,
            "global_flag": global_flag,
        },
    }

    return overview


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    # DATA_DIR piloté par la détection standard NSC (get_data_dir)
    data_dir = get_data_dir()
    logger.info("[sector_engine_pro] DATA_DIR=%s", data_dir)

    overview = compute_sector_engine(data_dir)

    out_path = data_dir / "analysis" / "sector_engine_pro.json"
    save_json_file(out_path, overview)
    logger.info(
        "[sector_engine_pro] sector_engine_pro.json sauvegardé (%s, nb_sectors=%d, global_flag=%s).",
        out_path,
        overview.get("stats", {}).get("nb_sectors", 0),
        overview.get("stats", {}).get("global_flag", "unknown"),
    )


if __name__ == "__main__":
    main()
