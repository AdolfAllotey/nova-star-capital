"""
hype_cycle_blocker_light.py
---------------------------

Brique "Hype Cycle Blocker" – Saison 1 (hedge fund light).

But :
- Détecter les assets en phase euphorique / parabolique.
- Produire un hype_score (0–100) et un flag hype_block_entry.
- Servir de garde-fou pour le moteur de signaux (signal_voting).

Entrées :
- data/analysis/momentum_scores.json
- data/market/microstructure_overview.json
- data/reports/sentiment_overview.json ou data/market/sentiment_overview.json
- data/analysis/narrative_overview.json (optionnel)

Sortie :
- data/analysis/hype_cycle_overview.json

Format :
{
  "bitcoin": {
    "symbol": "bitcoin",
    "timestamp": "...",
    "hype_score": 72.5,
    "hype_phase": "late_trend",
    "hype_block_entry": true,
    "components": {
      "momentum_meta": ...,
      "momentum_score": ...,
      "dist_ma20": ...,
      "volatility_score": ...,
      "sentiment_norm": ...,
      "narrative_score": ...,
      "price_extension_score": ...,
      "sentiment_score_component": ...,
      "volatility_component": ...,
      "momentum_component": ...,
      "narrative_component": ...
    },
    "tags": ["hype_late_trend", "hype_block_entry"]
  },
  ...
}
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("hype_cycle_blocker_light")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
MARKET_DIR = DATA_DIR / "market"
ANALYSIS_DIR = DATA_DIR / "analysis"
REPORTS_DIR = DATA_DIR / "reports"

MARKET_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MOMENTUM_FILE = ANALYSIS_DIR / "momentum_scores.json"
MICROSTRUCTURE_FILE = MARKET_DIR / "microstructure_overview.json"
SENTIMENT_REPORT_FILE = REPORTS_DIR / "sentiment_overview.json"
SENTIMENT_MARKET_FILE = MARKET_DIR / "sentiment_overview.json"
NARRATIVE_FILE = ANALYSIS_DIR / "narrative_overview.json"

OUTPUT_FILE = ANALYSIS_DIR / "hype_cycle_overview.json"

logger.info("[hype_cycle_blocker_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any = None) -> Any:
    return load_json_file(str(path), default=default)


def _save_json(path: Path, data: Any) -> None:
    save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Dataclasses & utils
# ---------------------------------------------------------------------------

@dataclass
class HypeCycleResult:
    symbol: str
    timestamp: str
    hype_score: float
    hype_phase: str  # early / expansion / late_trend / euphoria
    hype_block_entry: bool
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
# Extraction des features par source
# ---------------------------------------------------------------------------

def _extract_momentum_features(
    momentum_entry: Dict[str, Any]
) -> Dict[str, float]:
    """
    momentum_entry est une ligne de momentum_scores.json :
    {
      "symbol": "...",
      "meta_score": ...,
      "components": {
         "momentum": ...,
         ...
      },
      "price_features": {
         "ret_fast": ...,
         "ret_slow": ...,
         "dist_ma20": ...,
         ...
      },
      ...
    }
    """
    meta_score = _safe_float(momentum_entry.get("meta_score"), 0.0)
    components = momentum_entry.get("components") or {}
    price_features = momentum_entry.get("price_features") or {}

    momentum_score = _safe_float(components.get("momentum"), 0.0)
    dist_ma20 = _safe_float(price_features.get("dist_ma20"), 0.0)
    ret_fast = _safe_float(price_features.get("ret_fast"), 0.0)
    ret_slow = _safe_float(price_features.get("ret_slow"), 0.0)

    return {
        "meta_score": meta_score,
        "momentum_score": momentum_score,
        "dist_ma20": dist_ma20,
        "ret_fast": ret_fast,
        "ret_slow": ret_slow,
    }


def _extract_sentiment_for_symbol(
    sentiment_overview: Any, symbol: str
) -> float:
    """
    Retourne un sentiment normalisé 0–1 pour un symbol.
    On essaie d'être robuste au format :
      - dictionnaire {symbol: {...}}
      - liste de dicts avec "symbol" ou "asset"
    On cherche les champs :
      - "score", "sentiment_score", "avg_sentiment" (dans [-1,1] ou [0,1])
    """
    entry: Optional[Dict[str, Any]] = None

    # cas dict par symbol
    if isinstance(sentiment_overview, dict):
        if symbol in sentiment_overview and isinstance(sentiment_overview[symbol], dict):
            entry = sentiment_overview[symbol]
        else:
            # certains formats : clé "assets" ou "data"
            for key in ("assets", "data", "items"):
                val = sentiment_overview.get(key)
                if isinstance(val, list):
                    for e in val:
                        if not isinstance(e, dict):
                            continue
                        sym = e.get("symbol") or e.get("asset") or e.get("token")
                        if sym and str(sym).lower() == symbol.lower():
                            entry = e
                            break
                if entry is not None:
                    break

    # cas liste brute
    elif isinstance(sentiment_overview, list):
        for e in sentiment_overview:
            if not isinstance(e, dict):
                continue
            sym = e.get("symbol") or e.get("asset") or e.get("token")
            if sym and str(sym).lower() == symbol.lower():
                entry = e
                break

    if not isinstance(entry, dict):
        return 0.5  # neutre

    raw = (
        entry.get("score")
        or entry.get("sentiment_score")
        or entry.get("avg_sentiment")
        or entry.get("compound")
        or 0.0
    )
    raw_f = _safe_float(raw, 0.0)

    # cas [-1,1]
    if -1.0 <= raw_f <= 1.0:
        norm = (raw_f + 1.0) / 2.0  # -1->0, 0->0.5, 1->1
    else:
        # cas [0,100] ou [0,1]
        if raw_f > 1.0:
            norm = raw_f / 100.0
        else:
            norm = raw_f
    return _clip(norm, 0.0, 1.0)


def _extract_narrative_for_symbol(
    narrative_overview: Any, symbol: str
) -> Dict[str, Any]:
    """
    Cherche un éventuel narrative_score et des tags de hype.
    """
    entry: Optional[Dict[str, Any]] = None

    if isinstance(narrative_overview, dict):
        if symbol in narrative_overview and isinstance(narrative_overview[symbol], dict):
            entry = narrative_overview[symbol]
    # autres formats -> on reste simple, on ne complexifie pas pour le moment

    if not isinstance(entry, dict):
        return {"score": 0.0, "tags": []}

    score = entry.get("narrative_score") or entry.get("score") or 0.0
    score_f = _safe_float(score, 0.0)
    tags = entry.get("tags") or entry.get("narrative_tags") or []
    if not isinstance(tags, list):
        tags = []

    return {"score": score_f, "tags": tags}


def _extract_microstructure_for_symbol(
    micro: Any, symbol: str
) -> Dict[str, float]:
    if not isinstance(micro, dict) or symbol not in micro:
        return {
            "volatility_score": 50.0,
        }
    entry = micro[symbol]
    if not isinstance(entry, dict):
        return {"volatility_score": 50.0}
    vol = _safe_float(entry.get("volatility_score"), 50.0)
    return {"volatility_score": vol}


# ---------------------------------------------------------------------------
# Scoring hype
# ---------------------------------------------------------------------------

def _compute_hype_for_asset(
    symbol: str,
    momentum_entry: Optional[Dict[str, Any]],
    micro: Any,
    sentiment_overview: Any,
    narrative_overview: Any,
) -> Optional[HypeCycleResult]:
    if momentum_entry is None:
        # pas de momentum => on ne score pas la hype
        return None

    m_features = _extract_momentum_features(momentum_entry)
    meta_score = m_features["meta_score"]
    momentum_score = m_features["momentum_score"]
    dist_ma20 = m_features["dist_ma20"]
    ret_fast = m_features["ret_fast"]
    ret_slow = m_features["ret_slow"]

    micro_features = _extract_microstructure_for_symbol(micro, symbol)
    volatility_score = micro_features["volatility_score"]

    sentiment_norm = _extract_sentiment_for_symbol(sentiment_overview, symbol)
    nar = _extract_narrative_for_symbol(narrative_overview, symbol)
    narrative_score = _safe_float(nar["score"], 0.0)
    narrative_tags: List[str] = nar["tags"]

    # 1) Momentum component (0–30)
    #    On prend meta_score + momentum_score pour approx.
    momentum_norm = _clip((meta_score + momentum_score) / 200.0, 0.0, 1.0)
    momentum_component = momentum_norm * 30.0

    # 2) Price extension (dist_ma20, ret_fast vs ret_slow) (0–30)
    #    Plus on est au-dessus de la MA20 et plus le ratio ret_fast/ret_slow est élevé,
    #    plus on est en extension.
    price_extension = 0.0
    # dist_ma20 : 0–0.3 (~0–30%)
    if dist_ma20 > 0:
        price_extension += _clip(dist_ma20 / 0.3, 0.0, 1.0) * 18.0  # max 18 pts

    ratio = 0.0
    if abs(ret_slow) > 1e-6:
        ratio = ret_fast / ret_slow
    # si ret_fast >> ret_slow, on est en accélération
    if ratio > 1.5 and ret_fast > 0 and ret_slow > 0:
        price_extension += _clip((ratio - 1.5) / 2.0, 0.0, 1.0) * 12.0  # max 12 pts

    price_extension_score = _clip(price_extension, 0.0, 30.0)

    # 3) Sentiment component (0–20)
    #    0.5 = neutre, on commence à vraiment monter >0.65
    if sentiment_norm <= 0.55:
        sentiment_component = sentiment_norm * 10.0  # max ~5.5
    else:
        # au-dessus de 0.55, on accélère le score
        sentiment_component = 5.5 + (sentiment_norm - 0.55) / 0.45 * 14.5
    sentiment_component = _clip(sentiment_component, 0.0, 20.0)

    # 4) Volatility component (0–10)
    volatility_component = _clip(volatility_score / 100.0 * 10.0, 0.0, 10.0)

    # 5) Narrative component (0–10)
    narrative_component = _clip(narrative_score / 100.0 * 7.0, 0.0, 7.0)
    # Bonus si tags de hype
    hype_keywords = (
        "meme",
        "parabolic",
        "fomo",
        "mania",
        "hype",
        "narrative_hot",
        "degenerate",
        "ai_mania",
        "gambling",
    )
    if any(
        isinstance(t, str) and any(k in t.lower() for k in hype_keywords)
        for t in narrative_tags
    ):
        narrative_component = _clip(narrative_component + 3.0, 0.0, 10.0)

    # Score total
    hype_score_raw = (
        momentum_component
        + price_extension_score
        + sentiment_component
        + volatility_component
        + narrative_component
    )
    hype_score = _clip(hype_score_raw, 0.0, 100.0)

    # Phase qualitative
    if hype_score < 25.0:
        phase = "early"
    elif hype_score < 50.0:
        phase = "expansion"
    elif hype_score < 75.0:
        phase = "late_trend"
    else:
        phase = "euphoria"

    # Règle de blocage d'entrée
    hype_block_entry = False
    if phase == "euphoria":
        hype_block_entry = True
    elif phase == "late_trend" and hype_score >= 65.0 and volatility_score >= 85.0:
        hype_block_entry = True

    tags: List[str] = []
    if phase == "euphoria":
        tags.append("hype_euphoria")
    elif phase == "late_trend":
        tags.append("hype_late_trend")
    elif phase == "expansion":
        tags.append("hype_expansion")
    else:
        tags.append("hype_early")

    if hype_block_entry:
        tags.append("hype_block_entry")

    result = HypeCycleResult(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
        hype_score=round(hype_score, 2),
        hype_phase=phase,
        hype_block_entry=hype_block_entry,
        components={
            "momentum_meta": meta_score,
            "momentum_score": momentum_score,
            "dist_ma20": dist_ma20,
            "ret_fast": ret_fast,
            "ret_slow": ret_slow,
            "volatility_score": volatility_score,
            "sentiment_norm": sentiment_norm,
            "narrative_score": narrative_score,
            "narrative_tags": narrative_tags,
            "momentum_component": round(momentum_component, 2),
            "price_extension_score": round(price_extension_score, 2),
            "sentiment_component": round(sentiment_component, 2),
            "volatility_component": round(volatility_component, 2),
            "narrative_component": round(narrative_component, 2),
        },
        tags=tags,
    )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_hype_cycle_overview() -> Dict[str, HypeCycleResult]:
    momentum_scores = _load_json(MOMENTUM_FILE, default=[])
    if not isinstance(momentum_scores, list):
        logger.warning(
            "[hype_cycle_blocker_light] momentum_scores.json invalide ou vide."
        )
        momentum_scores = []

    micro = _load_json(MICROSTRUCTURE_FILE, default={})
    sentiment = _load_json(SENTIMENT_REPORT_FILE, default=None)
    if sentiment is None:
        sentiment = _load_json(SENTIMENT_MARKET_FILE, default={})
    if not sentiment:
        logger.warning(
            "[hype_cycle_blocker_light] Aucun sentiment_overview trouvé (reports ou market)."
        )

    narrative = _load_json(NARRATIVE_FILE, default={})

    # indexer momentum par symbol
    momentum_by_symbol: Dict[str, Dict[str, Any]] = {}
    for row in momentum_scores:
        if not isinstance(row, dict):
            continue
        sym = row.get("symbol")
        if not sym:
            continue
        momentum_by_symbol[str(sym).lower()] = row

    # union des symbols connus via momentum (driver principal)
    results: Dict[str, HypeCycleResult] = {}
    for sym_lower, m_entry in momentum_by_symbol.items():
        symbol = m_entry.get("symbol") or sym_lower
        try:
            res = _compute_hype_for_asset(
                symbol=symbol,
                momentum_entry=m_entry,
                micro=micro,
                sentiment_overview=sentiment,
                narrative_overview=narrative,
            )
        except Exception:
            logger.exception(
                "[hype_cycle_blocker_light] Erreur dans le calcul hype pour %s",
                symbol,
            )
            res = None

        if res is not None:
            results[symbol] = res

    logger.info(
        "[hype_cycle_blocker_light] Hype cycle calculé pour %d assets.",
        len(results),
    )
    return results


def save_hype_cycle_overview(results: Dict[str, HypeCycleResult]) -> None:
    payload = {sym: r.to_dict() for sym, r in results.items()}
    _save_json(OUTPUT_FILE, payload)
    logger.info(
        "[hype_cycle_blocker_light] Résultats sauvegardés dans %s.",
        OUTPUT_FILE,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    results = compute_hype_cycle_overview()
    if not results:
        logger.warning(
            "[hype_cycle_blocker_light] Aucun résultat hype (momentum_scores vide ?)."
        )
    save_hype_cycle_overview(results)


if __name__ == "__main__":
    main()
