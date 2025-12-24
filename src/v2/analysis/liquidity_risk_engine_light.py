# src/v2/analysis/liquidity_risk_engine_light.py

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

# On ne dépend plus de get_data_dir : on suit le pattern des autres *light
ROOT_DIR: Path = Path.cwd()
DATA_DIR: Path = ROOT_DIR / "data"
ANALYSIS_DIR: Path = DATA_DIR / "analysis"
MARKET_DIR: Path = DATA_DIR / "market"

OUTPUT_PATH: Path = ANALYSIS_DIR / "liquidity_risk_overview.json"


# ---------------------------------------------------------------------------
# Helpers pour extraire les champs de manière robuste
# ---------------------------------------------------------------------------


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip() != "":
            return float(value)
    except (ValueError, TypeError):
        return default
    return default


def _get_first_numeric(d: Dict[str, Any], keys: List[str]) -> Optional[float]:
    for k in keys:
        if k in d:
            v = _safe_float(d.get(k), None)
            if v is not None:
                return v
    return None


def _is_major_symbol(symbol: str) -> bool:
    symbol = (symbol or "").lower()
    majors = {
        "btc",
        "bitcoin",
        "eth",
        "ethereum",
        "sol",
        "solana",
        "bnb",
        "xrp",
        "avax",
        "matic",
    }
    return symbol in majors


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LiquidityStats:
    symbol: str
    volume_24h_usd: Optional[float]
    market_cap_usd: Optional[float]
    spread_pct: Optional[float]
    atr_pct: Optional[float]
    volatility_24h: Optional[float]
    volatility_7d: Optional[float]
    volume_to_mc_ratio: Optional[float]
    score: float
    flag: str
    reasons: List[str]


# ---------------------------------------------------------------------------
# Chargement des inputs
# ---------------------------------------------------------------------------


def _load_price_action_features() -> List[Dict[str, Any]]:
    """
    Charge price_action_features.json.
    Formats robustes :
    - liste de dicts
    - ou dict avec clé 'assets' contenant la liste
    """
    path = ANALYSIS_DIR / "price_action_features.json"
    data = load_json_file(path, default=[])

    assets: List[Dict[str, Any]] = []

    if isinstance(data, list):
        assets = data
    elif isinstance(data, dict):
        maybe_assets = data.get("assets")
        if isinstance(maybe_assets, list):
            assets = maybe_assets
        else:
            logger.warning(
                "[liquidity_risk_engine_light] price_action_features.json dict sans 'assets' exploitable (%s).",
                path,
            )
            assets = []
    else:
        logger.warning(
            "[liquidity_risk_engine_light] price_action_features.json au format inattendu (%s).",
            type(data),
        )
        assets = []

    logger.info(
        "[liquidity_risk_engine_light] price_action_features chargés depuis %s (n=%d).",
        path,
        len(assets),
    )
    return assets


def _load_mm_withdrawal() -> Dict[str, Any]:
    """
    Charge mm_withdrawal_overview.json si présent (optionnel).
    On ramène un dict par symbole :
      { "btc": {...}, "eth": {...}, ... }
    """
    path = ANALYSIS_DIR / "mm_withdrawal_overview.json"
    data = load_json_file(path, default={})
    if not data:
        return {}

    per_symbol: Dict[str, Dict[str, Any]] = {}

    # Formats possibles :
    # 1) {"assets": [{"symbol": "...", "flag": ...}, ...]}
    # 2) {"btc": {...}, "eth": {...}}
    if isinstance(data, dict):
        assets = data.get("assets")
        if isinstance(assets, list):
            for item in assets:
                if not isinstance(item, dict):
                    continue
                sym = str(item.get("symbol", "")).lower()
                if not sym:
                    continue
                per_symbol[sym] = item
        else:
            for key, value in data.items():
                if not isinstance(value, dict):
                    continue
                sym = str(value.get("symbol", key)).lower()
                per_symbol[sym] = value
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            sym = str(item.get("symbol", "")).lower()
            if sym:
                per_symbol[sym] = item

    logger.info(
        "[liquidity_risk_engine_light] mm_withdrawal_overview chargé (%d symboles).",
        len(per_symbol),
    )
    return per_symbol


def _load_narrative_flags() -> Dict[str, Dict[str, Any]]:
    """
    Charge narrative_overview.json si présent (optionnel).
    On récupère des flags narratifs pour chaque symbole.
    """
    path = ANALYSIS_DIR / "narrative_overview.json"
    data = load_json_file(path, default={})
    by_symbol: Dict[str, Dict[str, Any]] = {}

    if not data:
        return by_symbol

    assets = None
    if isinstance(data, dict):
        maybe_assets = data.get("assets")
        if isinstance(maybe_assets, list):
            assets = maybe_assets
    elif isinstance(data, list):
        assets = data

    if not assets:
        return by_symbol

    for item in assets:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol", "")).lower()
        if not sym:
            continue
        by_symbol[sym] = item

    logger.info(
        "[liquidity_risk_engine_light] narrative_overview chargé (%d symboles).",
        len(by_symbol),
    )
    return by_symbol


# ---------------------------------------------------------------------------
# Scoring de la liquidité
# ---------------------------------------------------------------------------


def _score_liquidity_for_asset(
    asset: Dict[str, Any],
    mm_by_symbol: Dict[str, Dict[str, Any]],
    narrative_by_symbol: Dict[str, Dict[str, Any]],
) -> LiquidityStats:
    symbol = str(asset.get("symbol") or asset.get("name") or "").lower()
    reasons: List[str] = []

    # Metrics de base
    volume_24h_usd = _get_first_numeric(
        asset,
        [
            "volume_24h_usd",
            "volume_usd_24h",
            "vol_24h_usd",
            "volume_24h",
            "volume_usd",
        ],
    )

    market_cap_usd = _get_first_numeric(
        asset,
        ["market_cap_usd", "market_cap", "mc_usd"],
    )

    spread_pct = _get_first_numeric(
        asset,
        ["spread_pct", "avg_spread_pct", "spread"],
    )

    atr_pct = _get_first_numeric(asset, ["atr_pct", "atr_14_pct", "atr_percent"])

    volatility_24h = _get_first_numeric(
        asset, ["volatility_24h", "vol_24h", "realized_vol_24h"]
    )
    volatility_7d = _get_first_numeric(
        asset, ["volatility_7d", "vol_7d", "realized_vol_7d"]
    )

    volume_to_mc_ratio: Optional[float] = None
    if (
        volume_24h_usd is not None
        and volume_24h_usd > 0
        and market_cap_usd is not None
        and market_cap_usd > 0
    ):
        volume_to_mc_ratio = volume_24h_usd / market_cap_usd

    # Score de base
    score = 100.0

    # --- 1) Volume & market cap ---
    if volume_24h_usd is None:
        score -= 20
        reasons.append("volume_24h_usd_inconnu")
    else:
        if volume_24h_usd < 50_000:
            score -= 40
            reasons.append("volume_24h_usd_tres_faible")
        elif volume_24h_usd < 250_000:
            score -= 25
            reasons.append("volume_24h_usd_faible")
        elif volume_24h_usd < 1_000_000:
            score -= 10
            reasons.append("volume_24h_usd_moyen")

    if market_cap_usd is None:
        score -= 10
        reasons.append("market_cap_inconnu")
    else:
        if market_cap_usd < 10_000_000:
            score -= 10
            reasons.append("small_cap")

    # --- 2) Ratio volume / market cap ---
    if volume_to_mc_ratio is not None:
        if volume_to_mc_ratio < 0.002:  # < 0,2% / jour
            score -= 20
            reasons.append("volume_to_mc_ratio_tres_faible")
        elif volume_to_mc_ratio < 0.01:  # < 1% / jour
            score -= 10
            reasons.append("volume_to_mc_ratio_faible")
        elif volume_to_mc_ratio > 0.3:
            score -= 5
            reasons.append("volume_to_mc_ratio_anormalement_eleve")

    # --- 3) Spread ---
    if spread_pct is None:
        reasons.append("spread_inconnu")
    else:
        sp = max(0.0, min(spread_pct, 100.0))
        if sp > 2.0:
            score -= 30
            reasons.append("spread_tres_eleve")
        elif sp > 1.0:
            score -= 20
            reasons.append("spread_eleve")
        elif sp > 0.5:
            score -= 10
            reasons.append("spread_moyen")

    # --- 4) Volatilité / ATR ---
    vol_metrics = [v for v in [volatility_24h, volatility_7d, atr_pct] if v is not None]
    vol_avg = sum(vol_metrics) / len(vol_metrics) if vol_metrics else None
    if vol_avg is not None:
        if vol_avg > 30.0:
            score -= 25
            reasons.append("volatilite_tres_elevee")
        elif vol_avg > 20.0:
            score -= 15
            reasons.append("volatilite_elevee")

    # --- 5) Bonus major (BTC/ETH/SOL...) ---
    if _is_major_symbol(symbol):
        score += 10
        reasons.append("major_asset_bonus")

    # --- 6) Market maker withdrawal ---
    mm_info = mm_by_symbol.get(symbol)
    if mm_info:
        mm_flag = str(mm_info.get("flag") or mm_info.get("status") or "").lower()
        if mm_flag in {"withdrawal", "at_risk", "critical"}:
            score -= 25
            reasons.append(f"mm_withdrawal_flag_{mm_flag}")

    # --- 7) Narratif (euphoria + faible liquidité) ---
    narr = narrative_by_symbol.get(symbol)
    if narr:
        flags = narr.get("narrative_flags") or narr.get("tags") or []
        if isinstance(flags, str):
            flags = [flags]
        hype_stage = str(narr.get("hype_stage", "")).lower()

        flags_lower = {str(f).lower() for f in flags}
        is_euphoria = "euphoria" in flags_lower or hype_stage in {
            "euphoria",
            "blowoff",
            "late_cycle",
        }
        if is_euphoria and (volume_24h_usd is None or volume_24h_usd < 1_000_000):
            score -= 20
            reasons.append("euphoria_avec_liquidite_limitee")

    score = max(0.0, min(score, 100.0))

    if score >= 75.0:
        flag = "ok"
    elif score >= 50.0:
        flag = "watch"
    else:
        flag = "risk"

    if not reasons:
        reasons.append("liquidite_ok")

    return LiquidityStats(
        symbol=symbol or "unknown",
        volume_24h_usd=volume_24h_usd,
        market_cap_usd=market_cap_usd,
        spread_pct=spread_pct,
        atr_pct=atr_pct,
        volatility_24h=volatility_24h,
        volatility_7d=volatility_7d,
        volume_to_mc_ratio=volume_to_mc_ratio,
        score=score,
        flag=flag,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Moteur principal
# ---------------------------------------------------------------------------


def compute_liquidity_risk() -> Dict[str, Any]:
    logger.info(
        "[liquidity_risk_engine_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR
    )

    assets_raw = _load_price_action_features()
    mm_by_symbol = _load_mm_withdrawal()
    narrative_by_symbol = _load_narrative_flags()

    if not assets_raw:
        logger.warning(
            "[liquidity_risk_engine_light] Aucun asset dans price_action_features.json, retour trivial."
        )
        overview = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nb_assets": 0,
            "nb_ok": 0,
            "nb_watch": 0,
            "nb_risk": 0,
            "global_flag": "unknown",
            "reason": "no_assets",
            "assets": [],
        }
        return overview

    stats: List[LiquidityStats] = []
    for a in assets_raw:
        if not isinstance(a, dict):
            continue
        s = _score_liquidity_for_asset(a, mm_by_symbol, narrative_by_symbol)
        stats.append(s)

    nb_assets = len(stats)
    nb_ok = sum(1 for s in stats if s.flag == "ok")
    nb_watch = sum(1 for s in stats if s.flag == "watch")
    nb_risk = sum(1 for s in stats if s.flag == "risk")

    if nb_assets == 0:
        global_flag = "unknown"
        reason = "no_assets"
    else:
        risk_ratio = nb_risk / nb_assets
        watch_ratio = nb_watch / nb_assets

        if nb_risk == 0 and risk_ratio < 0.05 and watch_ratio < 0.3:
            global_flag = "ok"
            reason = "liquidity_globally_ok"
        elif risk_ratio <= 0.3:
            global_flag = "caution"
            reason = "some_assets_illiquid"
        else:
            global_flag = "danger"
            reason = "too_many_illiquid_assets"

    assets_sorted = sorted(stats, key=lambda s: s.score)

    overview_assets: List[Dict[str, Any]] = []
    for s in assets_sorted:
        overview_assets.append(
            {
                "symbol": s.symbol,
                "liquidity_score": s.score,
                "flag": s.flag,
                "reasons": s.reasons,
                "metrics": {
                    "volume_24h_usd": s.volume_24h_usd,
                    "market_cap_usd": s.market_cap_usd,
                    "volume_to_mc_ratio": s.volume_to_mc_ratio,
                    "spread_pct": s.spread_pct,
                    "atr_pct": s.atr_pct,
                    "volatility_24h": s.volatility_24h,
                    "volatility_7d": s.volatility_7d,
                },
            }
        )

    overview: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nb_assets": nb_assets,
        "nb_ok": nb_ok,
        "nb_watch": nb_watch,
        "nb_risk": nb_risk,
        "global_flag": global_flag,
        "reason": reason,
        "assets": overview_assets,
    }

    return overview


def main() -> None:
    overview = compute_liquidity_risk()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_json_file(OUTPUT_PATH, overview)
    logger.info(
        "[liquidity_risk_engine_light] liquidity_risk_overview.json sauvegardé (%s, nb_assets=%d, global_flag=%s).",
        OUTPUT_PATH,
        overview.get("nb_assets", 0),
        overview.get("global_flag", "unknown"),
    )


if __name__ == "__main__":
    main()
