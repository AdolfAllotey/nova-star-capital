from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf


ROOT = Path("/opt/nsc/data/preprod/equities_offensive")

SHORTLIST_PATH = ROOT / "universe/shortlist_nasdaq.json"

METRICS_OUT = ROOT / "universe/metrics_snapshot_v2.json"
SNAPSHOT_OUT = ROOT / "universe/price_snapshot_v2.json"
UNIVERSE_OUT = ROOT / "universe/universe_filtered_v2.json"
PRICES_OUT = ROOT / "market/prices_v2.json"
QUALITY_OUT = ROOT / "market/data_quality_v2.json"

MIN_HISTORY_DAYS = 200
MIN_COVERAGE_RATIO = 0.80


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        if math.isfinite(result):
            return result
    except Exception:
        pass
    return default


def get_symbol_frame(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()

    frame: pd.DataFrame

    if isinstance(raw.columns, pd.MultiIndex):
        level_0 = set(str(x) for x in raw.columns.get_level_values(0))
        level_1 = set(str(x) for x in raw.columns.get_level_values(1))

        if symbol in level_0:
            frame = raw[symbol].copy()
        elif symbol in level_1:
            frame = raw.xs(symbol, axis=1, level=1).copy()
        else:
            return pd.DataFrame()
    else:
        frame = raw.copy()

    columns = {str(col).lower(): col for col in frame.columns}
    required = ("open", "high", "low", "close", "volume")

    if not all(name in columns for name in required):
        return pd.DataFrame()

    normalized = pd.DataFrame(
        {
            "Open": pd.to_numeric(frame[columns["open"]], errors="coerce"),
            "High": pd.to_numeric(frame[columns["high"]], errors="coerce"),
            "Low": pd.to_numeric(frame[columns["low"]], errors="coerce"),
            "Close": pd.to_numeric(frame[columns["close"]], errors="coerce"),
            "Volume": pd.to_numeric(frame[columns["volume"]], errors="coerce"),
        }
    )

    normalized = normalized.dropna(subset=["Close"])
    normalized = normalized[normalized["Close"] > 0]

    return normalized.sort_index()


def period_return(frame: pd.DataFrame, sessions: int) -> float:
    if len(frame) <= sessions:
        return 0.0

    current = safe_float(frame["Close"].iloc[-1])
    previous = safe_float(frame["Close"].iloc[-sessions - 1])

    if current <= 0 or previous <= 0:
        return 0.0

    return current / previous - 1.0


def atr_percentage(frame: pd.DataFrame, period: int = 14) -> float:
    if len(frame) < period + 1:
        return 0.0

    previous_close = frame["Close"].shift(1)

    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous_close).abs(),
            (frame["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    close = safe_float(frame["Close"].iloc[-1])

    if close <= 0:
        return 0.0

    return safe_float(true_range.tail(period).mean() / close)


def percentile_ranks(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}

    ordered = sorted(values.items(), key=lambda item: item[1])
    denominator = max(1, len(ordered) - 1)

    return {
        symbol: round(rank / denominator * 100.0, 2)
        for rank, (symbol, _) in enumerate(ordered)
    }


def main() -> int:
    shortlist = load_json(SHORTLIST_PATH, {}) or {}

    symbols = [
        str(symbol).upper().strip()
        for symbol in shortlist.get("symbols", [])
        if str(symbol).strip()
    ]

    symbols = list(dict.fromkeys(symbols))

    if not symbols:
        raise RuntimeError(f"No symbols available in {SHORTLIST_PATH}")

    print(f"Downloading {len(symbols)} symbols from yfinance...")

    raw = yf.download(
        tickers=symbols,
        period="18mo",
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )

    frames: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}

    for symbol in symbols:
        frame = get_symbol_frame(raw, symbol)

        if frame.empty:
            failures[symbol] = "missing_or_invalid_download"
            continue

        if len(frame) < MIN_HISTORY_DAYS:
            failures[symbol] = f"insufficient_history:{len(frame)}"
            continue

        close = safe_float(frame["Close"].iloc[-1])

        if close <= 0.10:
            failures[symbol] = f"invalid_close:{close}"
            continue

        frames[symbol] = frame

    return_126 = {
        symbol: period_return(frame, 126)
        for symbol, frame in frames.items()
    }

    relative_strength = percentile_ranks(return_126)

    metrics: dict[str, Any] = {}
    snapshots: dict[str, Any] = {}
    live_prices: dict[str, float] = {}

    for symbol, frame in frames.items():
        close = safe_float(frame["Close"].iloc[-1])
        volume = safe_float(frame["Volume"].iloc[-1])

        avg_dollar_volume_20d = safe_float(
            (frame["Close"].tail(20) * frame["Volume"].tail(20)).mean()
        )

        average_volume_20d = safe_float(frame["Volume"].tail(20).mean())

        last_market_date = str(frame.index[-1])

        metrics[symbol] = {
            "avg_dollar_vol_20d": round(avg_dollar_volume_20d, 2),
            "rs_6m": relative_strength.get(symbol, 0.0),
            "ret_60d": round(period_return(frame, 60), 6),
            "ret_126d": round(return_126.get(symbol, 0.0), 6),
            "atr_pct_14": round(atr_percentage(frame), 6),
            "history_days": len(frame),
            "last_market_date": last_market_date,
        }

        snapshots[symbol] = {
            "close": round(close, 6),
            "ma20": round(safe_float(frame["Close"].tail(20).mean()), 6),
            "ma50": round(safe_float(frame["Close"].tail(50).mean()), 6),
            "ma200": round(safe_float(frame["Close"].tail(200).mean()), 6),
            "hh_20": round(safe_float(frame["High"].tail(20).max()), 6),
            "ll_20": round(safe_float(frame["Low"].tail(20).min()), 6),
            "ret_20": round(period_return(frame, 20), 6),
            "vol_ratio": round(
                volume / average_volume_20d if average_volume_20d > 0 else 0.0,
                6,
            ),
            "volume": round(volume, 2),
            "history_days": len(frame),
            "last_market_date": last_market_date,
        }

        live_prices[symbol] = round(close, 6)

    filters = {
        "min_dollar_vol_20d": 500_000_000.0,
        "min_rs_6m": 55.0,
        "min_ret_60d": -0.02,
        "max_atr_pct_14": 0.06,
    }

    kept: list[str] = []
    dropped: dict[str, Any] = {}

    for symbol in symbols:
        metric = metrics.get(symbol)

        if metric is None:
            dropped[symbol] = {
                "reasons": [failures.get(symbol, "missing_metrics")],
                "metrics": {},
            }
            continue

        reasons: list[str] = []

        if metric["avg_dollar_vol_20d"] < filters["min_dollar_vol_20d"]:
            reasons.append("low_dollar_volume")

        if metric["rs_6m"] < filters["min_rs_6m"]:
            reasons.append("weak_relative_strength")

        if metric["ret_60d"] < filters["min_ret_60d"]:
            reasons.append("weak_60d_return")

        if metric["atr_pct_14"] > filters["max_atr_pct_14"]:
            reasons.append("excessive_volatility")

        if reasons:
            dropped[symbol] = {
                "reasons": reasons,
                "metrics": metric,
            }
        else:
            kept.append(symbol)

    requested_count = len(symbols)
    valid_count = len(frames)
    coverage_ratio = valid_count / requested_count if requested_count else 0.0

    quality_status = (
        "healthy"
        if coverage_ratio >= MIN_COVERAGE_RATIO and valid_count > 0
        else "degraded"
    )

    timestamp = utc_now_iso()

    write_json_atomic(
        METRICS_OUT,
        {
            "ts": timestamp,
            "engine": "offensive_market_data_refresher_v2",
            "source": "yfinance",
            "auto_adjust": True,
            "metrics": metrics,
        },
    )

    write_json_atomic(
        SNAPSHOT_OUT,
        {
            "ts": timestamp,
            "engine": "offensive_market_data_refresher_v2",
            "source": "yfinance",
            "auto_adjust": True,
            "prices": snapshots,
        },
    )

    write_json_atomic(
        UNIVERSE_OUT,
        {
            "ts": timestamp,
            "engine": "offensive_universe_builder_v2",
            "source": "yfinance",
            "universe": shortlist.get("universe", "nasdaq_core"),
            "filters": filters,
            "count_in": requested_count,
            "count_out": len(kept),
            "symbols": kept,
            "dropped": dropped,
        },
    )

    write_json_atomic(
        PRICES_OUT,
        {
            "ts": timestamp,
            "engine": "offensive_market_data_refresher_v2",
            "source": "yfinance",
            "auto_adjust": True,
            "universe": shortlist.get("universe", "nasdaq_core"),
            "prices": live_prices,
        },
    )

    anomalies = {
        symbol: reason
        for symbol, reason in failures.items()
        if reason.startswith("invalid_close")
    }

    quality_payload = {
        "ts": timestamp,
        "engine": "offensive_market_data_quality_v2",
        "status": quality_status,
        "source": "yfinance",
        "requested_symbols": requested_count,
        "valid_symbols": valid_count,
        "coverage_ratio": round(coverage_ratio, 4),
        "minimum_coverage_ratio": MIN_COVERAGE_RATIO,
        "universe_count": len(kept),
        "failures": failures,
        "anomalies": anomalies,
        "blocking": quality_status != "healthy",
    }

    write_json_atomic(QUALITY_OUT, quality_payload)

    print(json.dumps(quality_payload, indent=2, ensure_ascii=False))

    return 0 if quality_status == "healthy" else 2


if __name__ == "__main__":
    raise SystemExit(main())
