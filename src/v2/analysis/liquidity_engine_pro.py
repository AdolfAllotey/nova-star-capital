"""
Liquidity Engine Pro
--------------------

Objectif :
- Lire la vue de liquidité existante (liquidity_risk_overview.json ou équivalent)
- Normaliser les données par asset
- Produire une vue institutionnelle simple :
    - régime de liquidité par asset (deep / ok / shallow / avoid)
    - compte des hard/soft vetos
    - résumé global pour la Risk Console / Meta-Score Pro

Ce module est volontairement tolérant :
- il supporte plusieurs formats possibles du JSON d'entrée,
- et se contente de faire au mieux avec les champs présents.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# chemins
# ---------------------------------------------------------------------------

# On ne dépend PAS de file_utils.get_root_dir (qui n'existe pas ici)
ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"

LIQ_INPUT_CANDIDATES = [
    ANALYSIS_DIR / "liquidity_risk_overview.json",
    ANALYSIS_DIR / "liquidity_overview.json",
]

OUTPUT_PATH = ANALYSIS_DIR / "liquidity_engine_pro.json"


# ---------------------------------------------------------------------------
# dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LiquidityFlags:
    micro_ok: bool = True
    orderbook_ok: bool = True
    spread_ok: bool = True
    hard_veto: bool = False
    soft_veto: bool = False


@dataclass
class LiquidityAssetView:
    symbol: str
    liquidity_score: float
    spread_bps: Optional[float]
    volume_score: Optional[float]
    regime: str
    reasons: List[str]
    flags: LiquidityFlags


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _find_input_file() -> Optional[str]:
    """
    Retourne le premier fichier de liquidité existant parmi les candidats.
    """
    for path in LIQ_INPUT_CANDIDATES:
        if path.exists():
            return str(path)
    return None


def _normalize_assets(raw: Any) -> List[Dict[str, Any]]:
    """
    Normalise la structure de liquidité en une liste d'assets.

    Formats possibles gérés :
    - liste directe : [ {symbol: ..., ...}, ... ]
    - dict avec clé 'assets': { assets: [ ... ] }
    - dict by_symbol: { "BTC": {...}, "ETH": {...}, ... }
    """
    if raw is None:
        return []

    # Cas 1 : liste directe
    if isinstance(raw, list):
        return [a for a in raw if isinstance(a, dict)]

    if isinstance(raw, dict):
        # Cas 2 : dict avec clé 'assets'
        if "assets" in raw and isinstance(raw["assets"], list):
            return [a for a in raw["assets"] if isinstance(a, dict)]

        # Cas 3 : dict by_symbol
        if all(isinstance(v, dict) for v in raw.values()):
            assets: List[Dict[str, Any]] = []
            for sym, payload in raw.items():
                if isinstance(payload, dict):
                    payload = dict(payload)
                    payload.setdefault("symbol", sym)
                    assets.append(payload)
            return assets

    logger.warning(
        "[liquidity_engine_pro] Format de données de liquidité non reconnu (%s), aucun asset exploitable.",
        type(raw),
    )
    return []


def _classify_asset(asset: Dict[str, Any]) -> LiquidityAssetView:
    symbol = str(asset.get("symbol") or asset.get("asset") or "?").lower()

    # Scores possibles : liquidity_score, score, liquidity_risk_score (inversé)
    liq_score = float(asset.get("liquidity_score") or asset.get("score") or 0.0)

    liq_risk_score = asset.get("liquidity_risk_score")
    if liq_score == 0.0 and isinstance(liq_risk_score, (int, float)):
        # On mappe un risque [0,100] vers un score de qualité [0,100]
        liq_score = max(0.0, 100.0 - float(liq_risk_score))

    spread_bps: Optional[float] = None
    raw_spread = asset.get("spread_bps") or asset.get("spread")
    if isinstance(raw_spread, (int, float)):
        spread_bps = float(raw_spread)

    volume_score: Optional[float] = None
    raw_vol = (
        asset.get("volume_score")
        or asset.get("vol_score")
        or asset.get("normalized_volume")
    )
    if isinstance(raw_vol, (int, float)):
        volume_score = float(raw_vol)

    reasons: List[str] = []
    flags = LiquidityFlags()

    # Règles simples sur les spreads
    if spread_bps is not None:
        if spread_bps > 80:
            flags.spread_ok = False
            reasons.append(f"Spread très large ({spread_bps:.0f} bps)")
        elif spread_bps > 40:
            reasons.append(f"Spread modéré ({spread_bps:.0f} bps)")

    # Règles sur le score de liquidité (qualité de liquidité)
    if liq_score >= 80:
        regime = "deep"
        reasons.append("Liquidité profonde")
    elif liq_score >= 60:
        regime = "ok"
        reasons.append("Liquidité correcte")
    elif liq_score >= 40:
        regime = "shallow"
        reasons.append("Liquidité moyenne / prudence")
        flags.soft_veto = True
    else:
        regime = "avoid"
        reasons.append("Liquidité insuffisante / à éviter")
        flags.hard_veto = True

    # On durcit le veto si spread mauvais et régime déjà fragile
    if not flags.spread_ok and regime in {"shallow", "avoid"}:
        flags.hard_veto = True

    return LiquidityAssetView(
        symbol=symbol,
        liquidity_score=liq_score,
        spread_bps=spread_bps,
        volume_score=volume_score,
        regime=regime,
        reasons=reasons,
        flags=flags,
    )


# ---------------------------------------------------------------------------
# core
# ---------------------------------------------------------------------------

def compute_liquidity_overview() -> Dict[str, Any]:
    input_path = _find_input_file()
    if not input_path:
        logger.warning(
            "[liquidity_engine_pro] Aucun fichier de liquidité trouvé parmi: %s",
            [str(p) for p in LIQ_INPUT_CANDIDATES],
        )
        assets_view: List[LiquidityAssetView] = []
    else:
        raw = load_json_file(input_path, default=[])
        assets_raw = _normalize_assets(raw)
        assets_view = [_classify_asset(a) for a in assets_raw]

    nb_assets = len(assets_view)

    by_regime = {
        "deep": 0,
        "ok": 0,
        "shallow": 0,
        "avoid": 0,
    }
    nb_hard_veto = 0
    nb_soft_veto = 0

    for av in assets_view:
        by_regime[av.regime] = by_regime.get(av.regime, 0) + 1
        if av.flags.hard_veto:
            nb_hard_veto += 1
        if av.flags.soft_veto:
            nb_soft_veto += 1

    # Flag global pour la Risk Console
    if nb_assets == 0:
        global_flag = "unknown"
    elif nb_hard_veto > 0 and nb_hard_veto >= nb_assets * 0.5:
        global_flag = "danger"
    elif by_regime["avoid"] + by_regime["shallow"] > by_regime["deep"] + by_regime["ok"]:
        global_flag = "caution"
    else:
        global_flag = "ok"

    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(input_path) if input_path else None,
        "stats": {
            "nb_assets": nb_assets,
            "by_regime": by_regime,
            "nb_hard_veto": nb_hard_veto,
            "nb_soft_veto": nb_soft_veto,
            "global_flag": global_flag,
        },
        "assets": [
            {
                "symbol": av.symbol,
                "liquidity_score": av.liquidity_score,
                "spread_bps": av.spread_bps,
                "volume_score": av.volume_score,
                "regime": av.regime,
                "reasons": av.reasons,
                "flags": asdict(av.flags),
            }
            for av in assets_view
        ],
    }

    logger.info(
        "[liquidity_engine_pro] Liquidité calculée pour %d assets (global_flag=%s, source=%s).",
        nb_assets,
        global_flag,
        input_path,
    )

    return overview


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    overview = compute_liquidity_overview()
    save_json_file(OUTPUT_PATH, overview)
    logger.info(
        "[liquidity_engine_pro] liquidity_engine_pro.json sauvegardé (%s, assets=%d).",
        OUTPUT_PATH,
        overview["stats"]["nb_assets"],
    )
    # Pour usage en mode `python -m ... | jq`
    import json
    import sys

    json.dump(overview, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
