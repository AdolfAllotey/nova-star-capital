import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev
from typing import Dict, List, Any, Optional

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.ohlcv_utils import ohlcv_v2_to_legacy_rows
from src.v2.utils.logger import get_logger

logger = get_logger(__name__)


# G152_VOLATILITY_FULL_HISTORY_V1
# Preserve the complete canonical 672-candle / 7-calendar-day 15m history.
# 672 candles yield 671 adjacent log-returns, which is exactly the governed
# structural window required by VolatilityParams.window_7d.
def _nsc_ohlcv_v2_to_legacy_rows(raw, max_points: int = 672):
    """
    Convertit ohlcv_combined.json v2:
      {timestamp, env, assets:[{symbol, candles:[{close|c|...}, ...]}]}
    -> format legacy attendu par du code existant:
      { "BTCUSDT":[{"close":...}, ...], ... }
    """
    if not isinstance(raw, dict):
        return raw

    assets = raw.get("assets")
    if not isinstance(assets, list):
        return raw

    def _get_close(c):
        if not isinstance(c, dict):
            return None
        for k in ("close", "c", "Close", "close_price", "closePrice"):
            v = c.get(k)
            if v is not None:
                try:
                    return float(v)
                except Exception:
                    return None
        return None

    out = {}
    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        if not isinstance(sym, str) or not sym.strip():
            continue

        candles = a.get("candles")
        if not isinstance(candles, list) or len(candles) < 10:
            continue

        closes = []
        for c in candles[-max_points:]:
            v = _get_close(c)
            if v is not None and v > 0:
                closes.append(v)

        if len(closes) >= 10:
            out[sym.strip().upper()] = [{"close": x} for x in closes]

    return out if out else raw


# Détection des répertoires (même logique que les autres *engine_light)
# On aligne avec le reste du projet : /opt/nsc/app comme racine
ROOT_DIR = Path(
    os.environ.get(
        "NSC_ROOT_DIR",
        Path(__file__).resolve().parents[3]  # .../app/src/v2/analysis -> parents[3] = /opt/nsc/app
    )
)
DATA_DIR = Path(os.environ.get("NSC_DATA_DIR", ROOT_DIR / "data"))


@dataclass
class VolatilityParams:
    # G152_VOLATILITY_TEMPORAL_SEMANTICS_V1
    #
    # Canonical OHLCV contract:
    #   interval = 15 minutes
    #   4 bars/hour
    #   96 bars/day
    #   672 candles/7 calendar days -> 671 adjacent log-returns
    #
    # IMPORTANT:
    # These windows are counts of 15-minute log-returns, not candle counts.
    # A dataset containing 672 candles contains exactly 671 adjacent returns.
    # 4h/24h use trailing return samples; the structural 7d baseline uses all
    # returns available from the canonical 672-candle history.
    window_4h: int = 16
    window_24h: int = 96
    window_7d: int = 671

    # Classification thresholds are intentionally left unchanged in D1.
    # They classify the non-annualised per-15m return dispersion.
    # Calibration is a separate governed change.
    calm_max: float = 0.02
    normal_max: float = 0.04
    high_max: float = 0.08

    # Tactical acceleration:
    # recent 4h dispersion materially above the 24h baseline.
    spike_ratio: float = 1.5


def _load_ohlcv() -> Dict[str, List[Dict[str, Any]]]:
    """
    Charge et normalise ohlcv_combined.json dans un format:
      - dict: { "BTCUSDT": [ {candle}, ... ], ... }
      - list: [ {"symbol":"BTCUSDT","candles":[...]}, ... ]
      - list: [ {"symbol":"BTCUSDT", ...candle fields...}, ... ]  (group-by symbol)
    Retour: dict symbol -> list[candles(dict)]
    """
    path = DATA_DIR / "market" / "ohlcv_combined.json"
    data = load_json_file(str(path), default=None)
    # NSC: support ohlcv_combined.json v2 (assets/candles)
    data = _nsc_ohlcv_v2_to_legacy_rows(data, max_points=672)

    if not data:
        logger.warning(
            "[volatility_engine_pro] ohlcv_combined.json vide ou introuvable (%s), "
            "volatility_engine_pro va sortir nb_assets=0",
            path,
        )
        return {}

    normalized: Dict[str, List[Dict[str, Any]]] = {}

    # Format 1: dict symbol -> list[candles]
    if isinstance(data, dict):
        for sym, candles in data.items():
            # --- Support format: data[sym] = {'close':[...],'high':[...],'low':[...]} ---
            if isinstance(candles, dict):
                closes = candles.get('close')
                highs  = candles.get('high')
                lows   = candles.get('low')
                if isinstance(closes, list) and len(closes) > 2:
                    n = len(closes)
                    # aligne high/low si présents, sinon None
                    if not isinstance(highs, list) or len(highs) != n:
                        highs = [None]*n
                    if not isinstance(lows, list) or len(lows) != n:
                        lows = [None]*n
                    candles = [{'close': float(closes[i]), 'high': (float(highs[i]) if highs[i] is not None else None), 'low': (float(lows[i]) if lows[i] is not None else None)} for i in range(n)]
                else:
                    candles = []
            if not isinstance(candles, list):
                continue
            normalized[str(sym)] = [c for c in candles if isinstance(c, dict)]
        return normalized

    # Format 2: list
    if isinstance(data, list):
        # Case A: list[{symbol, candles}]
        for item in data:
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol") or item.get("ticker")
            if sym and isinstance(item.get("candles"), list):
                normalized[str(sym)] = [c for c in item["candles"] if isinstance(c, dict)]
        if normalized:
            return normalized

        # Case B: list[candle dict] with symbol -> group-by
        for c in data:
            if not isinstance(c, dict):
                continue
            sym = c.get("symbol") or c.get("ticker")
            if not sym:
                continue
            normalized.setdefault(str(sym), []).append(c)
        return normalized

    logger.warning(
        "[volatility_engine_pro] Format inattendu pour ohlcv_combined.json (%s), type=%s",
        path, type(data),
    )
    return {}


def _extract_closes(candles: List[Dict[str, Any]]) -> List[float]:
    """
    Extrait les prix de clôture en essayant plusieurs clés possibles: 'close' ou 'c'.
    Trie les bougies par timestamp si possible.
    """
    if not candles:
        return []

    def _ts_key(c: Dict[str, Any]) -> Any:
        # On essaie plusieurs champs pour l'ordonnancement
        for k in ("timestamp", "time", "t"):
            if k in c:
                return c[k]
        return 0

    sorted_candles = sorted(candles, key=_ts_key)
    closes: List[float] = []

    for c in sorted_candles:
        close = c.get("close")
        if close is None:
            close = c.get("c")
        if close is None:
            continue
        try:
            closes.append(float(close))
        except (TypeError, ValueError):
            continue

    return closes


def _compute_log_returns(closes: List[float]) -> List[float]:
    """Log-returns successifs sur une série de prix de clôture."""
    if len(closes) < 2:
        return []
    rets: List[float] = []
    for prev, cur in zip(closes[:-1], closes[1:]):
        try:
            if prev <= 0 or cur <= 0:
                continue
            rets.append(math.log(cur / prev))
        except Exception:
            continue
    return rets


def _rolling_volatility(rets: List[float], window: int) -> Optional[float]:
    """
    Population standard deviation of log-returns over an exact trailing
    temporal window.

    G152_STRICT_VOLATILITY_WINDOW_V1:
    a canonical horizon is valid only when the complete requested number
    of returns is available. Partial windows must not masquerade as
    4h / 24h / 7d measurements.
    """
    if window < 2:
        return None
    if len(rets) < window:
        return None

    window_rets = rets[-window:]

    try:
        return float(pstdev(window_rets))
    except Exception:
        return None


def _classify_vol(vol_long: Optional[float], params: VolatilityParams) -> str:
    """Retourne un régime de volatilité: calm / normal / high / extreme / unknown."""
    if vol_long is None:
        return "unknown"
    if vol_long < params.calm_max:
        return "calm"
    if vol_long < params.normal_max:
        return "normal"
    if vol_long < params.high_max:
        return "high"
    return "extreme"


def compute_volatility_overview(params: Optional[VolatilityParams] = None) -> Dict[str, Any]:
    """
    Calcule l'overview de volatilité à partir d'ohlcv_combined.json
    et renvoie une structure prête à être sérialisée en JSON.
    """
    if params is None:
        params = VolatilityParams()

    ohlcv_by_symbol = _load_ohlcv()
    assets: List[Dict[str, Any]] = []

    for symbol, candles in ohlcv_by_symbol.items():
        closes = _extract_closes(candles)
        rets = _compute_log_returns(closes)

        if len(rets) < 3:
            # Série trop courte, on log mais on ne s'arrête pas
            logger.debug(
                "[volatility_engine_pro] Série insuffisante pour %s (len_rets=%d)",
                symbol,
                len(rets),
            )
            continue

        # G152 temporal contract:
        # 15m OHLCV -> 4h / 24h / 7d realised-volatility horizons.
        vol_4h = _rolling_volatility(rets, params.window_4h)
        vol_24h = _rolling_volatility(rets, params.window_24h)
        vol_7d = _rolling_volatility(rets, params.window_7d)

        if vol_4h is None and vol_24h is None and vol_7d is None:
            continue

        vol_ratio_4h_24h = None
        if vol_4h is not None and vol_24h is not None and vol_24h > 0:
            vol_ratio_4h_24h = vol_4h / vol_24h

        vol_ratio_24h_7d = None
        if vol_24h is not None and vol_7d is not None and vol_7d > 0:
            vol_ratio_24h_7d = vol_24h / vol_7d

        # 24h is the canonical tactical regime horizon.
        # 7d is retained as the structural short baseline.
        regime = _classify_vol(vol_24h, params)

        vol_spike = bool(
            vol_4h is not None
            and vol_24h is not None
            and vol_24h > 0
            and vol_4h > params.spike_ratio * vol_24h
        )

        extreme_vol = regime == "extreme"

        assets.append(
            {
                "symbol": symbol,
                "vol_4h": vol_4h,
                "vol_24h": vol_24h,
                "vol_7d": vol_7d,
                "vol_ratio_4h_24h": vol_ratio_4h_24h,
                "vol_ratio_24h_7d": vol_ratio_24h_7d,

                # Temporary compatibility aliases.
                # They preserve downstream schema compatibility during the
                # governed migration but MUST NOT be interpreted as their
                # historical names implied.
                "vol_30d": vol_24h,
                "vol_ratio_7_30": vol_ratio_4h_24h,
                "legacy_aliases_deprecated": True,
                "vol_regime": regime,
                "flags": {
                    "vol_spike": vol_spike,
                    "extreme_vol": extreme_vol,
                },
            }
        )

    # Stats globales
    by_regime: Dict[str, int] = {}
    nb_spikes = 0
    nb_extreme = 0

    for a in assets:
        regime = a.get("vol_regime", "unknown")
        by_regime[regime] = by_regime.get(regime, 0) + 1
        flags = a.get("flags") or {}
        if flags.get("vol_spike"):
            nb_spikes += 1
        if flags.get("extreme_vol"):
            nb_extreme += 1

    overview: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(DATA_DIR / "market" / "ohlcv_combined.json"),
        "params": {
            "interval": "15m",
            "window_4h_bars": params.window_4h,
            "window_24h_bars": params.window_24h,
            "window_7d_returns": params.window_7d,
            "source_history_candles": 672,
            "temporal_semantics": "15m_realised_volatility",
            "legacy_aliases_deprecated": True,
            "thresholds": {
                "calm_max": params.calm_max,
                "normal_max": params.normal_max,
                "high_max": params.high_max,
                "calibration_status": "provisional_preprod",
            },
            "spike_ratio": params.spike_ratio,
        },
        "stats": {
            "nb_assets": len(assets),
            "by_regime": by_regime,
            "nb_vol_spike": nb_spikes,
            "nb_extreme_vol": nb_extreme,
        },
        "assets": assets,
    }

    logger.info(
        "[volatility_engine_pro] Volatilité calculée pour %d assets (source=%s).",
        len(assets),
        overview["source"],
    )
    return overview


def main() -> None:
    """Point d'entrée CLI: calcule et sauvegarde volatility_engine_pro.json."""
    out_path = DATA_DIR / "analysis" / "volatility_engine_pro.json"
    overview = compute_volatility_overview()
    save_json_file(out_path, overview)
    logger.info(
        "[volatility_engine_pro] volatility_engine_pro.json sauvegardé (%s, assets=%d).",
        out_path,
        overview["stats"]["nb_assets"],
    )


if __name__ == "__main__":
    main()
