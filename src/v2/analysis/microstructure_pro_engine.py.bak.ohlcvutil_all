"""
microstructure_pro_engine.py
-------------------------------
Bloc B – Microstructure Pro pour Nova Star Capital (Saison 1 avancée).

Objectifs :
  - Lire :
      * data/market/ohlcv_combined.json
      * data/market/microstructure_overview.json (si présent)
      * data/reports/sentiment_overview.json (sentiment par asset)
  - Calculer par asset :
      * depth_proxy_score (approximation de la profondeur/liquidité)
      * relative_strength (vs benchmark) & relative_strength_score
      * sentiment_price_divergence & sentiment_price_divergence_score
      * flags : rs_ok, divergence_negative
  - Mettre à jour les scores microstructure utilisés par momentum_scoring :
      * spread_score
      * depth_score
      * volatility_score
  - Sauvegarder dans :
      * data/market/microstructure_overview.json

Heuristiques (simplifiées, version PRO mais sans carnets d'ordres réels) :
  - Depth proxy : basée sur le volume récent et la volatilité (plus de volume, moins
    de volatilité = meilleure profondeur).
  - Relative strength : performance 7j de l'asset vs benchmark (bitcoin si dispo,
    sinon moyenne du marché).
  - Sentiment-price divergence : divergence entre sentiment moyen (0–1) et la
    performance prix 7j normalisée.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt, tanh
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("microstructure_pro_engine")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
MARKET_DIR = DATA_DIR / "market"
REPORTS_DIR = DATA_DIR / "reports"

MARKET_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OHLCV_FILE = MARKET_DIR / "ohlcv_combined.json"
MICRO_FILE = MARKET_DIR / "microstructure_overview.json"
SENTIMENT_FILE = REPORTS_DIR / "sentiment_overview.json"

logger.info(
    "[microstructure_pro_engine] ROOT_DIR=%s, DATA_DIR=%s",
    ROOT_DIR,
    DATA_DIR,
)

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
                "[microstructure_pro_engine] Erreur lors du chargement JSON: %s",
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
                "[microstructure_pro_engine] Erreur lors de l'écriture JSON: %s",
                path,
            )
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_list(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    return []


def _extract_series(
    candles: List[Dict[str, Any]],
    key_main: str,
    key_alt: Optional[str] = None,
) -> List[float]:
    res: List[float] = []
    for c in candles:
        v = c.get(key_main)
        if v is None and key_alt:
            v = c.get(key_alt)
        res.append(_safe_float(v, 0.0))
    return res


def _pct_change(xs: List[float], lag: int) -> float:
    n = len(xs)
    if n <= lag or lag <= 0:
        return 0.0
    prev = xs[-lag - 1]
    cur = xs[-1]
    if prev == 0:
        return 0.0
    return (cur - prev) / prev


def _stddev(xs: List[float]) -> float:
    n = len(xs)
    if n <= 1:
        return 0.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return sqrt(var)


def _load_ohlcv() -> Dict[str, Any]:
    data = _load_json(OHLCV_FILE, default={})
    if not isinstance(data, dict):
        logger.warning(
            "[microstructure_pro_engine] ohlcv_combined.json invalide, type=%s",
            type(data),
        )
        return {}
    return data


def _load_micro_base() -> Dict[str, Any]:
    data = _load_json(MICRO_FILE, default={})
    if not isinstance(data, dict):
        return {}
    return data


def _load_sentiment() -> Dict[str, Any]:
    data = _load_json(SENTIMENT_FILE, default={})
    if not isinstance(data, dict):
        return {}
    return data


# ---------------------------------------------------------------------------
# Core heuristics : depth proxy, RS, divergence
# ---------------------------------------------------------------------------

def _compute_depth_proxy(
    closes: List[float],
    volumes: List[float],
    lookback: int = 30,
) -> float:
    """
    Depth proxy simple :
      - volume moyen récent
      - volatilité récente (std des returns)
      -> plus de volume et moins de volatilité = score élevé.
    """
    n = len(closes)
    if n < lookback + 2:
        lookback = max(10, n - 2)
    if n < 5:
        return 50.0

    window_prices = closes[-lookback:]
    window_vols = volumes[-lookback:] if volumes else [0.0] * lookback

    # returns simples (pour la vol)
    returns: List[float] = []
    for i in range(1, len(window_prices)):
        prev = window_prices[i - 1]
        cur = window_prices[i]
        if prev != 0:
            returns.append((cur - prev) / prev)
        else:
            returns.append(0.0)

    vol_mean = sum(window_vols) / max(len(window_vols), 1)
    vol_std = _stddev(returns)

    # normalisation très simple
    # plus vol_mean est élevé → plus score up
    # plus vol_std est élevé → plus score down
    vol_mean_norm = min(vol_mean, 1e9)  # clamp pour éviter les délires
    depth = 50.0

    # volume moyen : on applique une fonction log-like simple
    if vol_mean_norm > 0:
        # pseudo log10 : on protège les très petits volumes
        depth += min(25.0, 10.0 * (vol_mean_norm ** 0.25))

    # volatilité : pénalité
    depth -= min(25.0, vol_std * 800.0)

    return max(0.0, min(100.0, depth))


def _compute_relative_strength(
    closes: List[float],
    benchmark_return_7d: float,
    lookback_days: int = 7,
) -> Tuple[float, float, bool]:
    """
    RS 7j vs benchmark (bitcoin ou moyenne marché).
      - retourne : rs_value (delta de perf), score 0–100, rs_ok bool
    """
    ret_7d = _pct_change(closes, lookback_days)
    rs_value = ret_7d - benchmark_return_7d

    # map rs_value ~ [-0.3, +0.3] → [0, 100]
    # 0.0 → 50
    if rs_value >= 0:
        rs_score = 50.0 + min(50.0, rs_value / 0.3 * 50.0)
    else:
        rs_score = 50.0 + max(-50.0, rs_value / 0.3 * 50.0)

    rs_score = max(0.0, min(100.0, rs_score))
    rs_ok = rs_score >= 55.0
    return rs_value, rs_score, rs_ok


def _compute_sentiment_price_divergence(
    closes: List[float],
    sentiment_score: float,
    lookback_days: int = 7,
) -> Tuple[float, float, bool]:
    """
    Divergence sentiment / prix :
      - sentiment_score : 0–1 (ex: 0.5 neutre)
      - ret_7d : converti en [0,1] via une fonction tanh-like
      - divergence = sentiment - price_norm
      - score = 0–100 basé sur |divergence|
      - divergence_negative : quand sentiment très optimiste et prix faible
        ou l'inverse (pessimiste mais prix très haussier).
    """
    ret_7d = _pct_change(closes, lookback_days)

    # normalisation des returns en [0,1] via tanh
    price_norm = 0.5 + 0.5 * tanh(ret_7d * 5.0)

    # clamp sentiment
    s = max(0.0, min(1.0, sentiment_score))
    divergence = s - price_norm

    # score basé sur l'ampleur de la divergence
    div_abs = abs(divergence)
    div_score = min(100.0, div_abs * 200.0)  # 0.5 d'écart -> 100

    # divergence "négative" = bull trap ou bear trap probables
    divergence_negative = False
    if s >= 0.7 and ret_7d <= 0:
        divergence_negative = True
    if s <= 0.3 and ret_7d >= 0.05:
        divergence_negative = True

    return divergence, div_score, divergence_negative


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def _build_micro_entry_for_symbol(
    symbol: str,
    candles: List[Dict[str, Any]],
    base_entry: Dict[str, Any],
    sentiment_entry: Dict[str, Any],
    benchmark_return_7d: float,
) -> Dict[str, Any]:
    candles_list = _safe_list(candles)
    if len(candles_list) < 10:
        logger.warning(
            "[microstructure_pro_engine] Trop peu de données pour %s (len=%d)",
            symbol,
            len(candles_list),
        )
        return base_entry

    closes = _extract_series(candles_list, "close", "c")
    volumes = _extract_series(candles_list, "volume", "v")

    # Depth proxy
    depth_proxy_score = _compute_depth_proxy(closes, volumes)

    # RS vs benchmark
    rs_value, rs_score, rs_ok = _compute_relative_strength(
        closes, benchmark_return_7d, lookback_days=7
    )

    # Sentiment
    s_score = _safe_float(sentiment_entry.get("sentiment_score"), 0.5)
    divergence, div_score, divergence_negative = _compute_sentiment_price_divergence(
        closes, s_score, lookback_days=7
    )

    # Volatilité + agrégation microstructure (pour compat avec momentum_scoring)
    # Volatilité simple sur 30 derniers points
    window = min(30, len(closes))
    window_prices = closes[-window:]
    returns: List[float] = []
    for i in range(1, len(window_prices)):
        prev = window_prices[i - 1]
        cur = window_prices[i]
        if prev != 0:
            returns.append((cur - prev) / prev)
        else:
            returns.append(0.0)
    vol_std = _stddev(returns)

    # On convertit vol_std en score : plus vol_std est élevé, plus le score baisse
    # approx : 0%->100, 5%->0 (ça se réajustera avec l'expérience)
    if vol_std <= 0:
        volatility_score = 80.0
    else:
        volatility_score = max(0.0, 100.0 - min(100.0, vol_std * 2000.0))

    # spread_score et depth_score : on utilise depth_proxy & RS pour affiner
    # base = 60, on ajoute/soustrait en fonction des signaux
    spread_score = 60.0
    depth_score = depth_proxy_score

    # RS bon → meilleure profondeur / spread
    if rs_ok:
        depth_score = min(100.0, depth_score + 10.0)
        spread_score = min(100.0, spread_score + 5.0)
    else:
        depth_score = max(0.0, depth_score - 10.0)
        spread_score = max(0.0, spread_score - 5.0)

    # divergence négative → pénalité sur spread / volatilité
    if divergence_negative:
        spread_score = max(0.0, spread_score - 10.0)
        volatility_score = max(0.0, volatility_score - 10.0)

    # Construction finale
    entry = dict(base_entry) if isinstance(base_entry, dict) else {}
    entry.update(
        {
            "spread_score": spread_score,
            "depth_score": depth_score,
            "volatility_score": volatility_score,
            "depth_proxy_score": depth_proxy_score,
            "relative_strength": rs_value,
            "relative_strength_score": rs_score,
            "rs_ok": rs_ok,
            "sentiment_price_divergence": divergence,
            "sentiment_price_divergence_score": div_score,
            "divergence_negative": divergence_negative,
            "sentiment_score": s_score,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return entry


def compute_microstructure_pro() -> Dict[str, Any]:
    ohlcv = _load_ohlcv()
    micro_base = _load_micro_base()
    sentiment = _load_sentiment()

    if not ohlcv:
        logger.warning(
            "[microstructure_pro_engine] Aucune donnée OHLCV dans %s.",
            OHLCV_FILE,
        )
        return {}

    # Calcul du benchmark 7j (bitcoin si dispo, sinon moyenne simple)
    benchmark_return_7d = 0.0
    if "bitcoin" in ohlcv:
        btc_closes = _extract_series(_safe_list(ohlcv["bitcoin"]), "close", "c")
        benchmark_return_7d = _pct_change(btc_closes, 7)
    else:
        rets: List[float] = []
        for candles in ohlcv.values():
            closes = _extract_series(_safe_list(candles), "close", "c")
            r = _pct_change(closes, 7)
            rets.append(r)
        if rets:
            benchmark_return_7d = sum(rets) / len(rets)

    logger.info(
        "[microstructure_pro_engine] Benchmark 7j (ret) = %.4f",
        benchmark_return_7d,
    )

    out: Dict[str, Any] = {}
    for symbol, candles in ohlcv.items():
        base_entry = micro_base.get(symbol, {})
        sentiment_entry = sentiment.get(symbol, {})
        out[symbol] = _build_micro_entry_for_symbol(
            symbol,
            _safe_list(candles),
            base_entry,
            sentiment_entry,
            benchmark_return_7d,
        )

    logger.info(
        "[microstructure_pro_engine] Microstructure Pro calculée pour %d assets.",
        len(out),
    )
    return out


def save_microstructure_pro(data: Dict[str, Any]) -> None:
    _save_json(MICRO_FILE, data)
    logger.info(
        "[microstructure_pro_engine] microstructure_overview.json mis à jour (%s, assets=%d).",
        MICRO_FILE,
        len(data),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    data = compute_microstructure_pro()
    if not data:
        logger.warning(
            "[microstructure_pro_engine] Aucun microstructure_pro généré."
        )
        return
    save_microstructure_pro(data)


if __name__ == "__main__":
    main()
