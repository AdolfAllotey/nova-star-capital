from __future__ import annotations
import datetime as dt

import os
import time
import secrets  # NSC_CORRELATION_RUN_ID_WRITER_V1
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.ohlcv_utils import ohlcv_v2_to_legacy_rows
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)

def _load_correlation_universe(data_dir: Path):
    """
    Lit data/market/correlation_universe.json:
      {"symbols":["BTCUSDT","ETHUSDT",...]}
    Retourne set(symbols_upper) ou None si absent/invalide.
    """
    try:
        from src.v2.utils.file_utils import load_json_file
        path = data_dir / "market" / "correlation_universe.json"
        raw = load_json_file(str(path), default={}) or {}
        if not isinstance(raw, dict):
            return None
        syms = raw.get("symbols")
        if not isinstance(syms, list) or not syms:
            return None
        out = set()
        for x in syms:
            if isinstance(x, str) and x.strip():
                out.add(x.strip().upper())
        return out if out else None
    except Exception:
        return None

def _matrix_to_pairs(matrix):
    """matrix: dict[a][b]=corr -> list of {a,b,corr}, uniquement off-diagonal."""
    if not isinstance(matrix, dict):
        return []
    pairs = []
    done = set()
    for a, row in matrix.items():
        if not isinstance(row, dict):
            continue
        for b, r in row.items():
            if a == b:
                continue
            if not isinstance(r, (int, float)):
                continue
            key = tuple(sorted((a, b)))
            if key in done:
                continue
            done.add(key)
            pairs.append({"a": a, "b": b, "corr": float(r)})
    return pairs

def _build_corr_matrix_from_ohlcv_v2(raw):
    """
    Construit une matrice de corrélation (Pearson) à partir de ohlcv_combined.json v2:
      {assets:[{symbol, candles:[{close,...}, ...]}]}
    Retour: dict[str, dict[str, float]]
    """
    if not isinstance(raw, dict):
        return {}
    assets = raw.get("assets")
    if not isinstance(assets, list) or not assets:
        return {}

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

    series = {}
    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        candles = a.get("candles")
        if not isinstance(sym, str) or not isinstance(candles, list):
            continue
        closes = []
        for c in candles:
            v = _get_close(c)
            if v is not None:
                closes.append(v)
        # il faut au moins 2 points pour corr
        if len(closes) >= 2:
            series[sym] = closes

    syms = sorted(series.keys())
    if len(syms) < 2:
        return {}

    def _pearson(x, y):
        n = min(len(x), len(y))
        if n < 2:
            return None
        x = x[-n:]
        y = y[-n:]
        mx = sum(x) / n
        my = sum(y) / n
        num = 0.0
        vx = 0.0
        vy = 0.0
        for i in range(n):
            dx = x[i] - mx
            dy = y[i] - my
            num += dx * dy
            vx += dx * dx
            vy += dy * dy
        if vx <= 0.0 or vy <= 0.0:
            return None
        return num / ((vx ** 0.5) * (vy ** 0.5))

    matrix = {}
    for i, a in enumerate(syms):
        matrix[a] = {}
        for j, b in enumerate(syms):
            if a == b:
                matrix[a][b] = 1.0
            elif b in matrix and a in matrix[b]:
                matrix[a][b] = matrix[b][a]
            else:
                r = _pearson(series[a], series[b])
                if r is not None:
                    matrix[a][b] = float(r)

    # Nettoyage: garder seulement les lignes non vides
    matrix = {k: v for k, v in matrix.items() if isinstance(v, dict) and len(v) > 0}
    return matrix

def _extract_close_series_from_ohlcv_v2(raw):
    """
    Supporte ohlcv_combined.json v2:
      {timestamp, env, assets:[{symbol, candles:[{close|c|...}, ...]}]}
    Retour: dict symbol -> list[float] closes (min 2 points)
    """
    if not isinstance(raw, dict):
        return {}
    assets = raw.get("assets")
    if not isinstance(assets, list):
        return {}

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
        candles = a.get("candles")
        if not isinstance(sym, str) or not isinstance(candles, list):
            continue
        closes = []
        for c in candles:
            v = _get_close(c)
            if v is not None:
                closes.append(v)
        if len(closes) >= 2:
            out[sym] = closes
    return out

def _count_ohlcv_symbols_v2(data_dir: Path) -> int:
    path = data_dir / "market" / "ohlcv_combined.json"
    try:
        from src.v2.utils.file_utils import load_json_file
        raw = load_json_file(str(path), default={})
        raw = ohlcv_v2_to_legacy_rows(raw)
    except Exception:
        return 0
    if not isinstance(raw, dict):
        return 0
    assets = raw.get("assets")
    if isinstance(assets, list):
        syms = []
        for a in assets:
            if isinstance(a, dict) and isinstance(a.get("symbol"), str):
                syms.append(a["symbol"])
        return len(set(syms))
    # legacy
    keys = [k for k in raw.keys() if k not in ("timestamp","env","meta","source","assets")]
    return len(keys)


def _normalize_ohlcv_combined(raw):
    """
    Return dict: symbol -> list[candles]
    Supports:
      - v2: { "assets": [ {"symbol": "...", "candles": [...]}, ... ] }
      - legacy: { "bitcoin": [...], "ethereum": [...] }
    """
    if not isinstance(raw, dict):
        return {}

    # v2 format
    assets = raw.get("assets")
    if isinstance(assets, list):
        out = {}
        for a in assets:
            if not isinstance(a, dict):
                continue
            sym = a.get("symbol") or a.get("id") or a.get("name")
            if not isinstance(sym, str) or not sym.strip():
                continue
            sym = sym.strip()

            candles = a.get("candles")
            if candles is None:
                candles = a.get("ohlcv")
            if candles is None:
                candles = a.get("data")

            if isinstance(candles, list) and len(candles) > 0:
                out[sym] = candles
        return out

    # legacy format
    out = {}
    for k, v in raw.items():
        if k in ("timestamp", "env", "meta", "source", "assets"):
            continue
        if isinstance(k, str) and isinstance(v, list) and len(v) > 0:
            out[k] = v
    return out


# Corrélation: éviter les hard-blocks sur un univers trop petit
MIN_PAIRS_FOR_PANIC = 10




def _nsc_build_corr_matrix_from_ohlcv(data_dir: Path, lookback: int = 120) -> dict:
    """
    Fallback: build a simple correlation matrix from data/market/ohlcv_combined.json.

    Supported formats:
      A) { "bitcoin":[{"close":...},...], "ethereum":[...], ... }
      B) { "bitcoin":{"close":[...], "high":[...], "low":[...]}, ... }

    Returns: {assetA:{assetB:corr,...}, ...}
    """
    try:
        from src.v2.utils.file_utils import load_json_file

        ohlcv_path = data_dir / "market" / "ohlcv_combined.json"
        obj = load_json_file(str(ohlcv_path), default={}) or {}
        obj = ohlcv_v2_to_legacy_rows(obj)
        if not isinstance(obj, dict) or not obj:
            return {}

        series = {}
        for asset, rows in obj.items():
            closes = []

            # Case A: list of candles
            if isinstance(rows, list) and rows:
                for r in rows[-lookback:]:
                    v = r.get("close") if isinstance(r, dict) else None
                    try:
                        if v is None:
                            continue
                        closes.append(float(v))
                    except Exception:
                        continue

            # Case B: dict with arrays (your current format)
            elif isinstance(rows, dict):
                c = rows.get("close")
                if isinstance(c, list) and c:
                    for v in c[-lookback:]:
                        try:
                            if v is None:
                                continue
                            closes.append(float(v))
                        except Exception:
                            continue

            if len(closes) >= 10:
                series[str(asset)] = closes

        assets = sorted(series.keys())
        if len(assets) < 2:
            return {}

        def corr(x, y):
            n = min(len(x), len(y))
            if n < 10:
                return None
            x = x[-n:]
            y = y[-n:]
            mx = sum(x) / n
            my = sum(y) / n
            num = sum((a - mx) * (b - my) for a, b in zip(x, y))
            denx = sum((a - mx) * (a - mx) for a in x)
            deny = sum((b - my) * (b - my) for b in y)
            den = (denx * deny) ** 0.5
            if den == 0:
                return None
            return num / den

        matrix = {a: {} for a in assets}
        for i, a in enumerate(assets):
            matrix[a][a] = 1.0
            for b in assets[i + 1:]:
                c = corr(series[a], series[b])
                if c is None:
                    continue
                matrix[a][b] = float(c)
                matrix[b][a] = float(c)

        return matrix
    except Exception:
        logger.exception("[correlation_regime_engine_pro] fallback matrix build failed")
        return {}

# G152_CORRELATION_V1_TEMPORAL_AUTHORITY
CORRELATION_WINDOW_RETURNS = 96
CORRELATION_MIN_ASSETS = 3
CORRELATION_MIN_RETURNS = 24
CORRELATION_MAX_SOURCE_AGE_HOURS = 1.0
CORRELATION_MAX_FUTURE_SKEW_MINUTES = 5.0


def _parse_utc_timestamp(value: Any) -> Optional[dt.datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        x = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if x.tzinfo is None:
            x = x.replace(tzinfo=dt.timezone.utc)
        return x.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _correlation_source_contract(
    data_dir: Path,
    now: Optional[dt.datetime] = None,
) -> Tuple[dict, Optional[dt.datetime], Optional[str]]:
    """
    Load canonical OHLCV and enforce temporal sovereignty.

    Returns:
      raw, source_timestamp, error_reason
    """
    path = data_dir / "market" / "ohlcv_combined.json"
    raw = load_json_file(str(path), default={}) or {}

    if not isinstance(raw, dict) or not raw:
        return {}, None, "missing_or_invalid_ohlcv"

    ts = _parse_utc_timestamp(raw.get("timestamp"))
    if ts is None:
        return raw, None, "missing_or_invalid_source_timestamp"

    now = now or dt.datetime.now(dt.timezone.utc)
    age_seconds = (now - ts).total_seconds()

    if age_seconds < -(CORRELATION_MAX_FUTURE_SKEW_MINUTES * 60.0):
        return raw, ts, "source_timestamp_in_future"

    if age_seconds > CORRELATION_MAX_SOURCE_AGE_HOURS * 3600.0:
        return raw, ts, "stale_ohlcv"

    return raw, ts, None


def _build_correlation_matrix_v1(
    raw: dict,
    window_returns: int = CORRELATION_WINDOW_RETURNS,
) -> Tuple[dict, dict]:
    """
    Authoritative Correlation V1 computation.

    - canonical OHLCV v2 input
    - log returns, never raw price levels
    - last `window_returns` returns
    - optional correlation_universe filtering is applied by caller
    """
    normalized = _normalize_ohlcv_combined(raw)

    returns: Dict[str, List[float]] = {}

    for symbol, candles in normalized.items():
        if not isinstance(candles, list):
            continue

        closes: List[float] = []
        for candle in candles:
            if not isinstance(candle, dict):
                continue
            value = None
            for key in ("close", "c", "Close", "close_price", "closePrice"):
                if candle.get(key) is not None:
                    value = candle.get(key)
                    break
            try:
                fv = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(fv) and fv > 0:
                closes.append(fv)

        rr: List[float] = []
        for i in range(1, len(closes)):
            a = closes[i - 1]
            b = closes[i]
            if a > 0 and b > 0:
                r = math.log(b / a)
                if math.isfinite(r):
                    rr.append(r)

        if len(rr) >= CORRELATION_MIN_RETURNS:
            returns[str(symbol)] = rr[-window_returns:]

    symbols = sorted(returns)
    matrix: Dict[str, Dict[str, float]] = {s: {s: 1.0} for s in symbols}

    def pearson(x: List[float], y: List[float]) -> Optional[float]:
        n = min(len(x), len(y))
        if n < CORRELATION_MIN_RETURNS:
            return None

        x = x[-n:]
        y = y[-n:]

        mx = sum(x) / n
        my = sum(y) / n

        vx = sum((v - mx) ** 2 for v in x)
        vy = sum((v - my) ** 2 for v in y)

        if vx <= 0.0 or vy <= 0.0:
            return None

        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        value = cov / math.sqrt(vx * vy)

        if not math.isfinite(value):
            return None

        return max(-1.0, min(1.0, float(value)))

    for i, a in enumerate(symbols):
        for b in symbols[i + 1:]:
            value = pearson(returns[a], returns[b])
            if value is None:
                continue
            matrix[a][b] = value
            matrix[b][a] = value

    matrix = {
        symbol: row
        for symbol, row in matrix.items()
        if isinstance(row, dict) and row
    }

    meta = {
        "assets_with_returns": len(symbols),
        "window_returns": int(window_returns),
        "min_returns": CORRELATION_MIN_RETURNS,
        "method": "pearson_log_returns",
    }
    return matrix, meta


def _apply_correlation_universe(matrix: dict, universe: Optional[set]) -> dict:
    if universe is None:
        return matrix

    out = {}
    for a, row in matrix.items():
        if str(a).upper() not in universe or not isinstance(row, dict):
            continue
        row2 = {
            b: value
            for b, value in row.items()
            if str(b).upper() in universe and isinstance(value, (int, float))
        }
        if row2:
            out[a] = row2
    return out


def _build_asset_correlations_v1(
    data_dir: Path,
    now: Optional[dt.datetime] = None,
) -> Tuple[dict, Optional[str]]:
    """
    Rebuild every cycle from canonical OHLCV.
    asset_correlations.json is an audit artifact, never an authoritative cache.
    """
    raw, source_ts, source_error = _correlation_source_contract(data_dir, now=now)

    if source_error is not None:
        return {
            "timestamp": (
                (now or dt.datetime.now(dt.timezone.utc))
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            ),
            "source": "ohlcv_combined",
            "source_generated_at": (
                source_ts.isoformat().replace("+00:00", "Z")
                if source_ts is not None else None
            ),
            "source_fresh": False,
            "matrix": {},
            "pairs": [],
            "error": source_error,
            "method": "pearson_log_returns",
            "window_returns": CORRELATION_WINDOW_RETURNS,
        }, source_error

    matrix, meta = _build_correlation_matrix_v1(
        raw,
        window_returns=CORRELATION_WINDOW_RETURNS,
    )

    universe = _load_correlation_universe(data_dir)
    matrix = _apply_correlation_universe(matrix, universe)

    now_utc = now or dt.datetime.now(dt.timezone.utc)
    age_h = max(0.0, (now_utc - source_ts).total_seconds() / 3600.0)

    wrapped = {
        "timestamp": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "ohlcv_combined",
        "source_generated_at": source_ts.isoformat().replace("+00:00", "Z"),
        "source_age_hours": age_h,
        "source_max_age_hours": CORRELATION_MAX_SOURCE_AGE_HOURS,
        "source_fresh": True,
        "method": meta["method"],
        "window_returns": meta["window_returns"],
        "min_returns": meta["min_returns"],
        "assets_count": len(matrix),
        "matrix": matrix,
        "pairs": _matrix_to_pairs(matrix),
    }
    wrapped["pair_count"] = len(wrapped["pairs"])
    return wrapped, None


def _nsc_ensure_asset_correlations_file(data_dir: Path) -> dict:
    """
    Compatibility wrapper.

    V1 deliberately does NOT reuse an existing asset_correlations.json.
    It rebuilds from current canonical OHLCV every run.
    """
    wrapped, _ = _build_asset_correlations_v1(data_dir)
    corr_file = data_dir / "analysis" / "asset_correlations.json"
    save_json_file(str(corr_file), wrapped)
    return wrapped

# ---------------------------------------------------------------------------
# Helpers locaux pour DATA_DIR et ENV
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """
    Renvoie le dossier data de NSC.

    - Si NSC_DATA_DIR est défini : on l'utilise.
    - Sinon : 'data' relatif au cwd (/opt/nsc/app).
    """
    base = os.getenv("NSC_DATA_DIR", "data")
    return Path(base).resolve()


def get_env() -> str:
    """Renvoie l'environnement courant ('PREPROD' par défaut)."""
    return os.getenv("NSC_ENV", "PREPROD")


# ---------------------------------------------------------------------------
# Dataclass & utilitaires de calcul
# ---------------------------------------------------------------------------

@dataclass
class CorrelationMetrics:
    nb_pairs: int
    avg_abs_corr: Optional[float]
    avg_pos_corr: Optional[float]
    avg_neg_corr: Optional[float]
    share_high_corr: float
    share_strong_neg: float


def _safe_append(values: List[float], value: Any) -> None:
    """Ajoute une valeur numérique à une liste si elle est valide."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return

    if math.isnan(v):
        return

    # Corrélation bornée dans [-1, 1]
    v = max(-1.0, min(1.0, v))
    values.append(v)


def compute_correlation_metrics(matrix: Dict[str, Dict[str, Any]]) -> CorrelationMetrics:
    """
    Calcule quelques métriques globales à partir d'une matrice de corrélation.

    matrix est supposée être du type :
    {
        "BTC": {"ETH": 0.8, "SOL": 0.6},
        "ETH": {"BTC": 0.8, "SOL": 0.5},
        ...
    }
    On ne compte chaque paire qu'une seule fois.
    """
    assets = sorted(matrix.keys())
    vals: List[float] = []
    pos_vals: List[float] = []
    neg_vals: List[float] = []

    nb_high_corr = 0       # |corr| >= 0.7
    nb_strong_neg = 0      # corr <= -0.5
    nb_pairs = 0

    for i, a in enumerate(assets):
        row = matrix.get(a, {})
        for b in assets[i + 1 :]:
            tmp: List[float] = []
            corr_raw = row.get(b)
            _safe_append(tmp, corr_raw)

            if not tmp:
                corr_raw = matrix.get(b, {}).get(a)
                _safe_append(tmp, corr_raw)

            if not tmp:
                continue

            corr = tmp[0]
            nb_pairs += 1
            vals.append(abs(corr))
            if corr >= 0:
                pos_vals.append(corr)
            else:
                neg_vals.append(corr)

            if abs(corr) >= 0.7:
                nb_high_corr += 1
            if corr <= -0.5:
                nb_strong_neg += 1

    if nb_pairs == 0:
        return CorrelationMetrics(
            nb_pairs=0,
            avg_abs_corr=None,
            avg_pos_corr=None,
            avg_neg_corr=None,
            share_high_corr=0.0,
            share_strong_neg=0.0,
        )

    def _avg(xs: List[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    return CorrelationMetrics(
        nb_pairs=nb_pairs,
        avg_abs_corr=_avg(vals),
        avg_pos_corr=_avg(pos_vals),
        avg_neg_corr=_avg(neg_vals),
        share_high_corr=nb_high_corr / nb_pairs if nb_pairs > 0 else 0.0,
        share_strong_neg=nb_strong_neg / nb_pairs if nb_pairs > 0 else 0.0,
    )


def infer_regime_and_score(metrics: CorrelationMetrics) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime global + flag de risque + score simple à partir des métriques.
    Retourne (regime, global_flag, score, reasons)
    """
    reasons: List[str] = []

    if metrics.nb_pairs == 0 or metrics.avg_abs_corr is None:
        reasons.append("Aucune donnée de corrélation exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    avg_abs = metrics.avg_abs_corr
    share_high = metrics.share_high_corr
    share_strong_neg = metrics.share_strong_neg

    if avg_abs >= 0.8 and share_high >= 0.6:
        regime = "panic"
        global_flag = "risk_off"
        score = 20.0
        reasons.append(
            f"Corrélation moyenne très élevée (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% des paires en corrélation forte."
        )
    elif avg_abs >= 0.6:
        regime = "high_corr"
        global_flag = "caution"
        score = 35.0
        reasons.append(
            f"Corrélation moyenne élevée (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% des paires en corrélation forte."
        )
    elif avg_abs >= 0.35:
        regime = "normal"
        global_flag = "neutral"
        score = 55.0
        reasons.append(
            f"Corrélations modérées (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% de corrélations fortes."
        )
    else:
        regime = "diversified"
        global_flag = "risk_on"
        score = 70.0
        reasons.append(
            f"Corrélations globalement faibles (|corr|≈{avg_abs:.2f}), "
            f"{share_high*100:.0f}% de corrélations fortes."
        )

    if share_strong_neg > 0.2:
        reasons.append(
            f"Part importante de corrélations fortement négatives "
            f"({share_strong_neg*100:.0f}% des paires ≤ -0.5)."
        )

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    """Map simple flag → sévérité d'event."""
    if global_flag == "risk_off":
        return "critical"
    if global_flag == "caution":
        return "warning"
    return "info"


def build_correlation_regime_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Authoritative Correlation V1 state.
    """
    raw = _nsc_ensure_asset_correlations_file(data_dir)

    matrix = raw.get("matrix", {}) if isinstance(raw, dict) else {}
    metrics = compute_correlation_metrics(matrix)

    source_fresh = bool(raw.get("source_fresh")) if isinstance(raw, dict) else False
    assets_count = int(raw.get("assets_count") or 0) if isinstance(raw, dict) else 0

    insufficient = (
        not source_fresh
        or assets_count < CORRELATION_MIN_ASSETS
        or metrics.nb_pairs < MIN_PAIRS_FOR_PANIC
    )

    if insufficient:
        regime = "unknown"
        global_flag = "caution"
        score = 50.0
        reasons = []

        if not source_fresh:
            reasons.append(
                f"Correlation source unavailable or stale: "
                f"{raw.get('error', 'source_not_fresh') if isinstance(raw, dict) else 'source_not_fresh'}."
            )
        if assets_count < CORRELATION_MIN_ASSETS:
            reasons.append(
                f"Correlation universe insufficient: assets={assets_count} "
                f"< {CORRELATION_MIN_ASSETS}."
            )
        if metrics.nb_pairs < MIN_PAIRS_FOR_PANIC:
            reasons.append(
                f"Correlation pair coverage insufficient: pairs={metrics.nb_pairs} "
                f"< {MIN_PAIRS_FOR_PANIC}."
            )
    else:
        regime, global_flag, score, reasons = infer_regime_and_score(metrics)

    severity = severity_from_flag(global_flag)
    now_ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "generated_at": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "source": "ohlcv_combined",
        "source_generated_at": raw.get("source_generated_at") if isinstance(raw, dict) else None,
        "source_age_hours": raw.get("source_age_hours") if isinstance(raw, dict) else None,
        "source_max_age_hours": CORRELATION_MAX_SOURCE_AGE_HOURS,
        "source_fresh": source_fresh,
        "method": "pearson_log_returns",
        "window_returns": CORRELATION_WINDOW_RETURNS,
        "assets_count": assets_count,
        "pair_count": metrics.nb_pairs,
        "metrics": {
            "nb_pairs": metrics.nb_pairs,
            "avg_abs_corr": metrics.avg_abs_corr,
            "avg_pos_corr": metrics.avg_pos_corr,
            "avg_neg_corr": metrics.avg_neg_corr,
            "share_high_corr": metrics.share_high_corr,
            "share_strong_neg": metrics.share_strong_neg,
        },
        "reasons": reasons,
    }

    logger.info(
        "[correlation_regime_engine_pro] env=%s regime=%s flag=%s "
        "score=%.2f assets=%d pairs=%d avg_abs_corr=%s source_fresh=%s",
        env,
        regime,
        global_flag,
        score,
        assets_count,
        metrics.nb_pairs,
        f"{metrics.avg_abs_corr:.4f}" if metrics.avg_abs_corr is not None else "None",
        source_fresh,
    )

    return state, severity


# === NSC_MACRO_RISK_V1 ===
def _compute_macro_risk_level(data_dir: str) -> str:
    """
    Read-only macro risk overlay based on:
      - analysis/nasdaq_regime_engine.json
      - analysis/dollar_regime_engine.json
    Returns: "low" | "neutral" | "medium" | "high"
    """
    try:
        from src.v2.utils.file_utils import load_json_file

        nasdaq = load_json_file(f"{data_dir}/analysis/nasdaq_regime_engine.json", default={}) or {}
        dollar = load_json_file(f"{data_dir}/analysis/dollar_regime_engine.json", default={}) or {}

        n_reg = str(nasdaq.get("regime", "neutral")).lower()
        d_reg = str(dollar.get("regime", "neutral")).lower()

        if n_reg == "risk_off" and d_reg != "weak":
            return "high"
        if n_reg == "risk_off" and d_reg == "weak":
            return "medium"
        if n_reg == "neutral" and d_reg == "strong":
            return "medium"
        if n_reg == "risk_on" and d_reg == "weak":
            return "low"
        return "neutral"
    except Exception:
        return "neutral"
# === END NSC_MACRO_RISK_V1 ===



def main() -> None:
    data_dir: Path = get_data_dir()
    env: str = get_env()

    logger.info(
        "[correlation_regime_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_correlation_regime_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "correlation_regime_engine_pro.json"
    # NSC_CORRELATION_RUN_ID_WRITER_V2
    try:
        if isinstance(state, dict):
            state['writer'] = 'correlation_regime_engine_pro'
            state['run_id'] = (str(os.environ.get('NSC_RUN_ID') or '').strip() or f"anon-{secrets.token_hex(8)}")
    except Exception:
        logger.exception('[correlation_regime_engine_pro] failed to attach writer/run_id')

    # G152_CORRELATION_CANONICAL_AUTHORITY_V1
    if isinstance(state, dict):
        _m = state.get('metrics') if isinstance(state.get('metrics'), dict) else {}
        state.setdefault('nb_pairs', _m.get('nb_pairs'))
        state.setdefault('avg_abs_corr', _m.get('avg_abs_corr'))
        state.setdefault('writer', 'correlation_regime_engine_pro')
        state.setdefault('schema_version', 2)

    _canon = output_path.with_name('correlation_regime.json')

    # Canonical authority is written only after the state is fully enriched.
    save_json_file(str(_canon), state)

    # Compatibility artifact must carry the same contract/state.
    save_json_file(str(output_path), state)
    logger.info(
        "[correlation_regime_engine_pro] correlation_regime_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication dans l’event bus
    publish_event(
        event_type="correlation.regime.state",
        source="correlation_regime_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[correlation_regime_engine_pro] Event correlation.regime.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
