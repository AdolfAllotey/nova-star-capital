"""
market_maker_withdrawal_light.py
--------------------------------

Brique "Market Maker Withdrawal Detector" – Saison 1 (hedge fund light).

Évalue si les market makers se retirent pour chaque asset
à partir de microstructure_overview.json.

Entrée :
  data/market/microstructure_overview.json

Sortie :
  data/analysis/mm_withdrawal_overview.json

Format :
{
  "bitcoin": {
    "symbol": "bitcoin",
    "timestamp": "...",
    "mm_withdrawal_score": 74.5,
    "withdrawal_detected": true,
    "components": {...},
    "tags": ["mm_withdrawal_strong"]
  },
  ...
}
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from src.v2.utils.logger import get_logger

logger = get_logger("market_maker_withdrawal_light")

# -------------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
MARKET_DIR = DATA_DIR / "market"
ANALYSIS_DIR = DATA_DIR / "analysis"

MARKET_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

MICROSTRUCTURE_FILE = MARKET_DIR / "microstructure_overview.json"
OUTPUT_FILE = ANALYSIS_DIR / "mm_withdrawal_overview.json"

logger.info("[mm_withdrawal_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)

# -------------------------------------------------------------------------
# File utils
# -------------------------------------------------------------------------

from src.v2.utils.file_utils import load_json_file, save_json_file

def _load_json(path: Path, default=None):
    return load_json_file(str(path), default=default)

def _save_json(path: Path, data: Any):
    save_json_file(str(path), data)

# -------------------------------------------------------------------------
# Dataclass
# -------------------------------------------------------------------------

@dataclass
class MMWithdrawalResult:
    symbol: str
    timestamp: str
    mm_withdrawal_score: float
    withdrawal_detected: bool
    components: Dict[str, Any]
    tags: List[str]

    def to_dict(self):
        return asdict(self)

# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _clip(x, lo, hi):
    return max(lo, min(hi, x))

# -------------------------------------------------------------------------
# Core logic
# -------------------------------------------------------------------------

def _compute_mm_withdrawal_for_asset(symbol: str, m: Dict[str, Any]) -> MMWithdrawalResult:
    spread_bps = _safe_float(m.get("spread_bps"), 10.0)
    depth_ratio = _safe_float(m.get("depth_ratio"), 1.0)
    spoof_prob = _safe_float(m.get("spoofing_probability"), 0.0)
    volatility_score = _safe_float(m.get("volatility_score"), 50.0)

    # Spread risk 0–40
    if spread_bps < 30:
        spread_risk = 5
    elif spread_bps > 180:
        spread_risk = 40
    else:
        spread_risk = 5 + (spread_bps - 30) / 150 * 35
    spread_risk = _clip(spread_risk, 0, 40)

    # Depth risk 0–30 (faible profondeur = plus de risque)
    if depth_ratio >= 0.8:
        depth_risk = 5
    elif depth_ratio <= 0.1:
        depth_risk = 30
    else:
        depth_risk = 5 + (0.8 - depth_ratio) / 0.7 * 25
    depth_risk = _clip(depth_risk, 0, 30)

    # Spoofing risk 0–20
    spoof_risk = _clip(spoof_prob * 20, 0, 20)

    # Volatility risk 0–10
    vol_risk = _clip(volatility_score / 100 * 10, 0, 10)

    mm_withdrawal_score = spread_risk + depth_risk + spoof_risk + vol_risk
    mm_withdrawal_score = round(mm_withdrawal_score, 2)

    withdrawal = mm_withdrawal_score >= 65

    tags = []
    if withdrawal:
        if mm_withdrawal_score >= 80:
            tags.append("mm_withdrawal_extreme")
        else:
            tags.append("mm_withdrawal_strong")
    else:
        if mm_withdrawal_score <= 25:
            tags.append("mm_normal")
        else:
            tags.append("mm_slight_risk")

    return MMWithdrawalResult(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
        mm_withdrawal_score=mm_withdrawal_score,
        withdrawal_detected=withdrawal,
        components={
            "spread_bps": spread_bps,
            "depth_ratio": depth_ratio,
            "spoofing_probability": spoof_prob,
            "volatility_score": volatility_score,
            "spread_risk": spread_risk,
            "depth_risk": depth_risk,
            "spoofing_risk": spoof_risk,
            "volatility_risk": vol_risk,
        },
        tags=tags,
    )

# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------

def compute_mm_withdrawal_overview() -> Dict[str, MMWithdrawalResult]:
    micro = _load_json(MICROSTRUCTURE_FILE, default={})
    if not micro:
        logger.warning("[mm_withdrawal_light] microstructure_overview.json introuvable")
        return {}

    results = {}
    for symbol, m in micro.items():
        try:
            res = _compute_mm_withdrawal_for_asset(symbol, m)
            results[symbol] = res
        except Exception:
            logger.exception(
                "[mm_withdrawal_light] Erreur calcul withdrawal %s", symbol
            )
    logger.info(
        "[mm_withdrawal_light] Withdrawal calculé pour %d assets", len(results)
    )
    return results


def save_mm_withdrawal_overview(results: Dict[str, MMWithdrawalResult]):
    payload = {sym: res.to_dict() for sym, res in results.items()}
    _save_json(OUTPUT_FILE, payload)
    logger.info("[mm_withdrawal_light] Résultats sauvegardés dans %s", OUTPUT_FILE)


def main():
    res = compute_mm_withdrawal_overview()
    save_mm_withdrawal_overview(res)


if __name__ == "__main__":
    main()
