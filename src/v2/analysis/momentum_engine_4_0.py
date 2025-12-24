# src/v2/analysis/momentum_engine_4_0.py

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"

MomentumRegime = Literal["strong_long", "long_bias", "neutral", "avoid", "block"]


@dataclass
class MomentumFlags:
    micro_ok: bool
    orderflow_ok: bool
    price_action_ok: bool
    avoid_liquidity_pool: bool
    hard_veto: bool
    soft_veto: bool


@dataclass
class MomentumAssetView:
    symbol: str
    meta_score: float
    momentum_score: float
    cycle_phase: Optional[str]
    cycle_phase_score: float
    regime: MomentumRegime
    flags: MomentumFlags
    reasons: List[str]


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _load_momentum_scores() -> List[Dict[str, Any]]:
    """
    Charge momentum_scores.json avec tolérance sur le format :
    - soit une liste directe d'assets
    - soit un dict avec clé "assets"
    """
    path = ANALYSIS_DIR / "momentum_scores.json"
    data = load_json_file(path, default=[])
    assets: List[Dict[str, Any]]

    if isinstance(data, list):
        assets = data
    elif isinstance(data, dict) and isinstance(data.get("assets"), list):
        assets = data["assets"]
    else:
        logger.warning(
            "[momentum_engine_4_0] Format inattendu pour momentum_scores.json (%s), utilisation liste vide.",
            type(data),
        )
        assets = []

    logger.info(
        "[momentum_engine_4_0] momentum_scores.json chargé (%s, n=%d).",
        path,
        len(assets),
    )
    return assets


def _extract_flags(asset: Dict[str, Any]) -> MomentumFlags:
    components = asset.get("components", {}) or {}
    filters = asset.get("filters", {}) or {}

    # On prend d'abord filters, sinon fallback components (qui contient déjà les booléens dans certains scripts)
    micro_ok = bool(filters.get("micro_ok", components.get("micro_ok", True)))
    orderflow_ok = bool(filters.get("orderflow_ok", components.get("orderflow_ok", True)))
    price_action_ok = bool(filters.get("price_action_ok", components.get("price_action_ok", True)))
    avoid_lp = bool(filters.get("avoid_liquidity_pool", components.get("avoid_liquidity_pool", False)))

    # Règles de veto institutionnel (v4.0 simplifiée)
    hard_veto = (not micro_ok) or (not orderflow_ok) or avoid_lp
    soft_veto = (not price_action_ok)

    return MomentumFlags(
        micro_ok=micro_ok,
        orderflow_ok=orderflow_ok,
        price_action_ok=price_action_ok,
        avoid_liquidity_pool=avoid_lp,
        hard_veto=hard_veto,
        soft_veto=soft_veto,
    )


def _classify_asset(asset: Dict[str, Any]) -> MomentumAssetView:
    symbol = str(asset.get("symbol") or asset.get("token") or "?")

    meta_score = _safe_float(asset.get("meta_score", 0.0))
    components = asset.get("components", {}) or {}
    momentum_score = _safe_float(components.get("momentum", meta_score))

    cycle_phase = components.get("cycle_phase") or asset.get("cycle_phase")
    cycle_phase_score = _safe_float(
        components.get("cycle_phase_score", asset.get("cycle_phase_score", 0.0))
    )

    flags = _extract_flags(asset)

    reasons: List[str] = []
    regime: MomentumRegime = "neutral"

    # --- Seuils (v4.0, version light institutionnelle) ---
    # On s'aligne sur une grille simple mais stricte :
    TH_STRONG = 70.0
    TH_LONG = 55.0
    TH_AVOID = 35.0
    BAD_CYCLE_PHASES = {"distribution", "capitulation"}

    # 1) Hard veto ⇒ "block"
    if flags.hard_veto:
        regime = "block"
        reasons.append("Hard veto : microstructure/orderflow/liq_pool KO")

    # 2) Cycle très défavorable ⇒ "avoid" si pas déjà "block"
    elif cycle_phase and cycle_phase.lower() in BAD_CYCLE_PHASES:
        regime = "avoid"
        reasons.append(f"Cycle défavorable : {cycle_phase}")

    # 3) Score très faible ⇒ "avoid"
    elif meta_score <= TH_AVOID:
        regime = "avoid"
        reasons.append(f"Meta score faible ({meta_score:.1f} ≤ {TH_AVOID})")

    # 4) Fort momentum & price action clean ⇒ "strong_long"
    elif (meta_score >= TH_STRONG) and flags.price_action_ok and not flags.soft_veto:
        regime = "strong_long"
        reasons.append(f"Momentum fort (meta ≥ {TH_STRONG}) et price action OK")

    # 5) Momentum correct ⇒ "long_bias"
    elif meta_score >= TH_LONG:
        regime = "long_bias"
        reasons.append(f"Momentum positif (meta ≥ {TH_LONG})")

    # 6) Sinon ⇒ "neutral"
    else:
        regime = "neutral"
        reasons.append("Momentum neutre / mitigé")

    # Affinage des raisons avec les flags
    if flags.soft_veto and regime in ("strong_long", "long_bias"):
        reasons.append("Soft veto : price action / structure à surveiller")

    if flags.avoid_liquidity_pool:
        reasons.append("Risque de pool de liquidité / rug")

    if not flags.micro_ok:
        reasons.append("Microstructure défavorable")

    if not flags.orderflow_ok:
        reasons.append("Orderflow défavorable")

    return MomentumAssetView(
        symbol=symbol,
        meta_score=meta_score,
        momentum_score=momentum_score,
        cycle_phase=cycle_phase,
        cycle_phase_score=cycle_phase_score,
        regime=regime,
        flags=flags,
        reasons=reasons,
    )


def compute_momentum_overview() -> Dict[str, Any]:
    assets_raw = _load_momentum_scores()
    views: List[MomentumAssetView] = [_classify_asset(a) for a in assets_raw]

    by_regime: Dict[MomentumRegime, int] = {
        "strong_long": 0,
        "long_bias": 0,
        "neutral": 0,
        "avoid": 0,
        "block": 0,
    }
    hard_veto_count = 0
    soft_veto_count = 0

    for v in views:
        by_regime[v.regime] += 1
        if v.flags.hard_veto:
            hard_veto_count += 1
        if v.flags.soft_veto:
            soft_veto_count += 1

    nb_assets = len(views)

    stats = {
        "nb_assets": nb_assets,
        "by_regime": by_regime,
        "nb_hard_veto": hard_veto_count,
        "nb_soft_veto": soft_veto_count,
        "parameters": {
            "thresholds": {
                "strong_long": 70.0,
                "long_bias": 55.0,
                "avoid": 35.0,
            },
            "bad_cycle_phases": ["distribution", "capitulation"],
        },
    }

    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(ANALYSIS_DIR / "momentum_scores.json"),
        "nb_assets": nb_assets,
        "stats": stats,
        "assets": [
            {
                **{
                    "symbol": v.symbol,
                    "meta_score": v.meta_score,
                    "momentum_score": v.momentum_score,
                    "cycle_phase": v.cycle_phase,
                    "cycle_phase_score": v.cycle_phase_score,
                    "regime": v.regime,
                    "reasons": v.reasons,
                },
                "flags": asdict(v.flags),
            }
            for v in views
        ],
    }

    logger.info(
        "[momentum_engine_4_0] Momentum calculé pour %d assets (source=%s).",
        nb_assets,
        overview["source_file"],
    )

    return overview


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYSIS_DIR / "momentum_engine_4_0.json"

    overview = compute_momentum_overview()
    save_json_file(out_path, overview)

    logger.info(
        "[momentum_engine_4_0] momentum_engine_4_0.json sauvegardé (%s, assets=%d).",
        out_path,
        overview.get("nb_assets", 0),
    )

    # Optionnel : JSON brut sur stdout (utile si tu pipes sans jq)
    try:
        print(json.dumps(overview, ensure_ascii=False))
    except BrokenPipeError:
        # Cas où on pipe vers head / jq et que le pipe est fermé en amont
        pass


if __name__ == "__main__":
    main()
