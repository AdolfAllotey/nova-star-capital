# src/v2/analysis/alpha_beta_engine.py
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("alpha_beta_engine")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _var(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _cov(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (len(xs) - 1)


def _corr(xs: List[float], ys: List[float]) -> Optional[float]:
    vx = _var(xs)
    vy = _var(ys)
    if vx <= 0 or vy <= 0:
        return None
    c = _cov(xs, ys)
    return c / math.sqrt(vx * vy)


def _beta_alpha(xs: List[float], ys: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    y = alpha + beta*x
    returns: beta, alpha, r2
    """
    vx = _var(xs)
    if vx <= 0 or len(xs) < 2 or len(xs) != len(ys):
        return None, None, None
    beta = _cov(xs, ys) / vx
    alpha = _mean(ys) - beta * _mean(xs)

    # R²
    my = _mean(ys)
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (alpha + beta * x)) ** 2 for x, y in zip(xs, ys))
    r2 = None
    if ss_tot > 0:
        r2 = 1.0 - (ss_res / ss_tot)
    return beta, alpha, r2


def _detect_btc_series(ohlcv: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Try to find BTC candles in a tolerant way.
    Expected shapes:
      - dict with keys per symbol: {"BTCUSDT":[...], "ETHUSDT":[...]}
      - dict with nested dict: {"symbols": {"BTCUSDT":[...]}}
      - list of candles already for BTC
    """
    if isinstance(ohlcv, list):
        return ohlcv

    if not isinstance(ohlcv, dict):
        return None

    candidates_keys = [
        "BTCUSDT", "BTC-USD", "BTCUSD", "BTC", "XBTUSD", "XBT"
    ]

    # 1) direct
    for k in candidates_keys:
        v = ohlcv.get(k)
        if isinstance(v, list) and v:
            return v

    # 2) nested common containers
    for container_key in ["symbols", "data", "ohlcv", "candles"]:
        cont = ohlcv.get(container_key)
        if isinstance(cont, dict):
            for k in candidates_keys:
                v = cont.get(k)
                if isinstance(v, list) and v:
                    return v

    return None


def _monthly_closes_from_candles(candles: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Returns dict month_label -> close
    candle keys tolerant: time/ts/date + close/c
    """
    month_close: Dict[str, float] = {}
    for c in candles:
        if not isinstance(c, dict):
            continue
        ts = c.get("time") or c.get("ts") or c.get("timestamp") or c.get("date")
        close = c.get("close") or c.get("c")
        close_f = _safe_float(close)
        if close_f is None or ts is None:
            continue

        # ts can be iso string, seconds, ms
        try:
            if isinstance(ts, (int, float)):
                # ms vs s heuristic
                t = int(ts)
                if t > 10_000_000_000:
                    dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
                else:
                    dt = datetime.fromtimestamp(t, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        label = f"{dt.year:04d}-{dt.month:02d}"
        # overwrite until last candle of the month encountered
        month_close[label] = close_f

    return month_close


def _returns_from_monthly_closes(month_close: Dict[str, float]) -> Tuple[List[str], List[float]]:
    labels = sorted(month_close.keys())
    rets: List[float] = []
    out_labels: List[str] = []
    prev: Optional[float] = None
    for lab in labels:
        px = month_close[lab]
        if prev is None or prev == 0:
            prev = px
            continue
        r = (px / prev) - 1.0
        out_labels.append(lab)
        rets.append(r)
        prev = px
    return out_labels, rets


def build_alpha_beta_overview(
    base_capital_eur: float = 5000.0,
) -> Dict[str, Any]:
    data_dir = Path(get_data_dir())

    # ---- 1) Strategy monthly returns (proxy)
    src = data_dir / "monthly_profitability.json"
    if not src.exists():
        # fallback path
        src = data_dir / "profitability" / "monthly_profitability.json"

    payload = load_json_file(str(src), default={})
    months = payload.get("months") if isinstance(payload, dict) else None
    if not isinstance(months, list) or not months:
        return {
            "as_of": _utc_now(),
            "benchmark": {"id": "BTC", "name": "BTC"},
            "bricks": [],
        }

    # label -> pnl
    pnl_by_month: Dict[str, float] = {}
    for m in months:
        if not isinstance(m, dict):
            continue
        lab = m.get("label")
        pnl = _safe_float(m.get("trading_pnl_eur"))
        if lab and pnl is not None:
            pnl_by_month[str(lab)] = pnl

    strat_labels = sorted(pnl_by_month.keys())
    # returns aligned to month labels (same labels as pnl months)
    strat_returns = [pnl_by_month[lab] / base_capital_eur for lab in strat_labels]

    # ---- 2) Benchmark monthly returns (BTC)
    bench_fp = data_dir / "market" / "ohlcv_combined.json"
    bench_returns: List[float] = []
    bench_labels: List[str] = []
    if bench_fp.exists():
        ohlcv = load_json_file(str(bench_fp), default=None)
        candles = _detect_btc_series(ohlcv)
        if candles:
            month_close = _monthly_closes_from_candles(candles)
            blabs, brets = _returns_from_monthly_closes(month_close)
            bench_labels, bench_returns = blabs, brets

    # ---- 3) Align by common labels (intersection)
    common = sorted(set(strat_labels) & set(bench_labels)) if bench_labels else []
    x = [bench_returns[bench_labels.index(lab)] for lab in common] if common else []
    y = [strat_returns[strat_labels.index(lab)] for lab in common] if common else []

    beta, alpha, r2 = (None, None, None)
    corr = None
    if len(x) >= 2 and len(y) >= 2:
        beta, alpha, r2 = _beta_alpha(x, y)
        corr = _corr(x, y)

    # volatility of strategy returns (on its own series)
    vol = math.sqrt(_var(strat_returns)) if len(strat_returns) >= 2 else None
    tot_ret = sum(strat_returns) if strat_returns else None

    out = {
        "as_of": _utc_now(),
        "benchmark": {"id": "BTC", "name": "BTC"},
        "bricks": [
            {
                "id": "crypto",
                "name": "Crypto",
                "alpha": alpha,
                "beta": beta,
                "r2": r2,
                "corr": corr,
                "return": tot_ret,          # cumul des retours mensuels (proxy)
                "volatility": vol,          # stddev mensuelle (proxy)
                "n_points": len(common) if common else len(strat_returns),
            }
        ],
        "meta": {
            "mode": "monthly_proxy",
            "base_capital_eur": base_capital_eur,
            "strategy_months": strat_labels,
            "benchmark_months": bench_labels,
            "aligned_months": common,
        },
    }
    return out


def write_overview_file(base_capital_eur: float = 5000.0) -> Path:
    data_dir = Path(get_data_dir())
    out_dir = data_dir / "analysis" / "alpha_beta"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_fp = out_dir / "alpha_beta_overview.json"

    overview = build_alpha_beta_overview(base_capital_eur=base_capital_eur)
    save_json_file(str(out_fp), overview)
    logger.info(f"[alpha_beta_engine] wrote {out_fp}")
    return out_fp


if __name__ == "__main__":
    fp = write_overview_file()
    print(str(fp))
