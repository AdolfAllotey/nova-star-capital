"""
liquidity_risk_light.py
-----------------------

Brique "Liquidity Pool Awareness" (Saison 1 – hedge fund light).

Objectif : évaluer le risque de liquidité par asset à partir de la microstructure.

Entrée :
- data/market/microstructure_overview.json
  (généré par ton moteur de microstructure, ex. :
   {
     "bitcoin": {
       "symbol": "bitcoin",
       "spread_bps": 25.0,
       "depth_ratio": 0.7,
       "spoofing_probability": 0.1,
       "depth_proxy_score": 74.9,
       "volatility_score": 99.8,
       ...
     },
     ...
   })

Sortie :
- data/analysis/liquidity_risk_overview.json

Format :
{
  "bitcoin": {
    "symbol": "bitcoin",
    "timestamp": "...",
    "liquidity_risk_score": 42.5,
    "avoid_liquidity_pool": false,
    "components": {
      "spread_bps": ...,
      "depth_ratio": ...,
      "spoofing_probability": ...,
      "spread_risk": ...,
      "depth_risk": ...,
      "volatility_risk": ...,
      "spoofing_risk": ...,
      "composite_risk": ...
    },
    "tags": ["liquidity_ok"]  # ou ["liquidity_risky"], ["liquidity_extreme"]
  },
  ...
}
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import math

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("liquidity_risk_light")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
MARKET_DIR = DATA_DIR / "market"
ANALYSIS_DIR = DATA_DIR / "analysis"

MARKET_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

MICROSTRUCTURE_FILE = MARKET_DIR / "microstructure_overview.json"
OUTPUT_FILE = ANALYSIS_DIR / "liquidity_risk_overview.json"

logger.info("[liquidity_risk_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)

# ---------------------------------------------------------------------------
# file_utils fallback
# ---------------------------------------------------------------------------

try:
    from src.v2.utils.file_utils import load_json_file, save_json_file  # type: ignore
except Exception:  # pragma: no cover
    load_json_file = None
    save_json_file = None

    import json

    def _load_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception(
                "[liquidity_risk_light] Erreur lors du chargement JSON: %s",
                path,
            )
            return default

    def _save_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                import json as _json

                _json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            logger.exception(
                "[liquidity_risk_light] Erreur lors de l'écriture JSON: %s",
                path,
            )
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Dataclasses & helpers
# ---------------------------------------------------------------------------

@dataclass
class LiquidityRiskResult:
    symbol: str
    timestamp: str
    liquidity_risk_score: float
    avoid_liquidity_pool: bool
    components: Dict[str, Any]
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Core scoring logic
# ---------------------------------------------------------------------------

def _compute_liquidity_risk_for_asset(symbol: str, data: Dict[str, Any]) -> LiquidityRiskResult:
    """
    Score de risque de liquidité 0–100 (0 = très liquide, 100 = très risqué).

    Idée :
      - spread_bps élevé  => risque ↑
      - depth_ratio faible => risque ↑
      - volatility_score élevé => risque ↑ (liquidations faciles)
      - spoofing_probability élevée => risque "fake liquidity"

    Pondérations :
      - spread_risk      0–35
      - depth_risk       0–25
      - volatility_risk  0–25
      - spoofing_risk    0–15
    """

    spread_bps = _safe_float(data.get("spread_bps"), 0.0)           # ex: 25 = 0.25%
    depth_ratio = _safe_float(data.get("depth_ratio"), 1.0)         # 0–1 : part de la taille d'ordre vs ref
    volatility_score = _safe_float(data.get("volatility_score"), 50.0)  # 0–100
    spoofing_prob = _safe_float(data.get("spoofing_probability"), 0.0)  # 0–1

    # 1) Spread risk
    #    <10 bps -> quasi 0
    #    10–50 bps -> interpolation
    #    >80 bps -> max
    if spread_bps <= 10.0:
        spread_risk = 2.0  # un petit plancher
    elif spread_bps >= 80.0:
        spread_risk = 35.0
    else:
        spread_risk = 2.0 + (spread_bps - 10.0) / (80.0 - 10.0) * (35.0 - 2.0)
    spread_risk = _clip(spread_risk, 0.0, 35.0)

    # 2) Depth risk
    #    depth_ratio proche de 1 => bonne profondeur => risque faible
    #    depth_ratio < 0.3 => profondeur faible
    if depth_ratio >= 1.0:
        depth_risk = 2.0
    elif depth_ratio <= 0.1:
        depth_risk = 25.0
    else:
        # interpolation inverse (plus c'est faible, plus c'est risqué)
        depth_risk = 2.0 + (1.0 - depth_ratio) * 23.0  # si 0.1 -> ~ 2 + 0.9*23
    depth_risk = _clip(depth_risk, 0.0, 25.0)

    # 3) Volatility risk
    #    On part du volatility_score microstructure (0–100)
    #    On mappe directement sur 0–25
    volatility_risk = volatility_score / 100.0 * 25.0
    volatility_risk = _clip(volatility_risk, 0.0, 25.0)

    # 4) Spoofing / fake liquidity risk
    #    0–1 -> 0–15
    spoofing_risk = spoofing_prob * 15.0
    spoofing_risk = _clip(spoofing_risk, 0.0, 15.0)

    # Composite
    composite_risk = spread_risk + depth_risk + volatility_risk + spoofing_risk
    liquidity_risk_score = _clip(composite_risk, 0.0, 100.0)

    # Décision "avoid_liquidity_pool" : on met un seuil raisonnable
    avoid = False
    if liquidity_risk_score >= 70.0:
        avoid = True
    if spread_bps >= 120.0:  # >1.2% de spread => extrême
        avoid = True
    if depth_ratio <= 0.15:  # profondeur quasi inexistante
        avoid = True

    tags: List[str] = []
    if avoid:
        if liquidity_risk_score >= 85.0:
            tags.append("liquidity_extreme")
        else:
            tags.append("liquidity_risky")
    else:
        if liquidity_risk_score <= 30.0:
            tags.append("liquidity_good")
        else:
            tags.append("liquidity_ok")

    result = LiquidityRiskResult(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
        liquidity_risk_score=round(liquidity_risk_score, 2),
        avoid_liquidity_pool=avoid,
        components={
            "spread_bps": spread_bps,
            "depth_ratio": depth_ratio,
            "volatility_score": volatility_score,
            "spoofing_probability": spoofing_prob,
            "spread_risk": round(spread_risk, 2),
            "depth_risk": round(depth_risk, 2),
            "volatility_risk": round(volatility_risk, 2),
            "spoofing_risk": round(spoofing_risk, 2),
            "composite_risk": round(liquidity_risk_score, 2),
        },
        tags=tags,
    )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_liquidity_risk_overview() -> Dict[str, LiquidityRiskResult]:
    micro = _load_json(MICROSTRUCTURE_FILE, default={})
    if not isinstance(micro, dict) or not micro:
        logger.warning(
            "[liquidity_risk_light] Aucun microstructure_overview trouvé dans %s.",
            MICROSTRUCTURE_FILE,
        )
        return {}

    results: Dict[str, LiquidityRiskResult] = {}
    for symbol, mdata in micro.items():
        if not isinstance(mdata, dict):
            continue
        try:
            res = _compute_liquidity_risk_for_asset(symbol, mdata)
        except Exception:
            logger.exception(
                "[liquidity_risk_light] Erreur lors du calcul du risque de liquidité pour %s",
                symbol,
            )
            continue
        results[symbol] = res

    logger.info(
        "[liquidity_risk_light] Liquidity risk calculé pour %d assets.",
        len(results),
    )
    return results


def save_liquidity_risk_overview(results: Dict[str, LiquidityRiskResult]) -> None:
    payload = {sym: res.to_dict() for sym, res in results.items()}
    _save_json(OUTPUT_FILE, payload)
    logger.info(
        "[liquidity_risk_light] Résultats sauvegardés dans %s.",
        OUTPUT_FILE,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    results = compute_liquidity_risk_overview()
    if not results:
        logger.warning(
            "[liquidity_risk_light] Aucun risque de liquidité calculé (aucune donnée ?)."
        )
    save_liquidity_risk_overview(results)


if __name__ == "__main__":
    main()
