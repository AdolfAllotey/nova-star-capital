# src/v2/api/routes/alpha_beta.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter

from src.v2.utils.file_utils import load_json_file, get_data_dir
from src.v2.utils.logger import get_logger

logger = get_logger("alpha_beta_routes")

PREFIX = "/alpha-beta"
router = APIRouter(tags=["alpha-beta"])

# -------------------------
# Helpers
# -------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def _month_key(label: str) -> str:
    # label = "YYYY-MM"
    return label.strip()

def _sum_flows_for_month(flows: List[Dict[str, Any]], month_label: str) -> float:
    # month_label "YYYY-MM"
    total = 0.0
    for f in flows or []:
        ts = str(f.get("ts", "")).strip()
        typ = str(f.get("type", "")).strip().lower()
        amt = _safe_float(f.get("amount_eur"))
        if not ts or amt is None:
            continue
        # month from ts
        try:
            m = ts[:7]  # "YYYY-MM"
        except Exception:
            continue
        if m != month_label:
            continue
        if typ == "deposit":
            total += amt
        elif typ == "withdraw":
            total -= amt
        elif typ == "transfer_in":
            total += amt
        elif typ == "transfer_out":
            total -= amt
        else:
            # ignore unknown types
            continue
    return total

def _compute_returns_from_equity(equity: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    # equity = [(month, V_end)]
    # returns aligned to month (return for that month vs previous month end)
    out: List[Tuple[str, float]] = []
    prev_v = None
    for month, v in equity:
        if prev_v is None or prev_v <= 0:
            out.append((month, 0.0))
        else:
            out.append((month, (v - prev_v) / prev_v))
        prev_v = v
    return out

def _std(xs: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return var ** 0.5

def _corr(xs: List[float], ys: List[float]) -> Optional[float]:
    n = min(len(xs), len(ys))
    if n < 2:
        return None
    x = xs[:n]
    y = ys[:n]
    mx = sum(x) / n
    my = sum(y) / n
    vx = sum((xi - mx) ** 2 for xi in x)
    vy = sum((yi - my) ** 2 for yi in y)
    if vx <= 0 or vy <= 0:
        return None
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    return cov / (vx ** 0.5 * vy ** 0.5)

def _linreg_alpha_beta(port: List[float], bench: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    # returns alpha (intercept), beta (slope), r2
    n = min(len(port), len(bench))
    if n < 2:
        return None, None, None
    x = bench[:n]
    y = port[:n]
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx <= 0:
        return None, None, None
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    beta = sxy / sxx
    alpha = my - beta * mx

    # r2
    yhat = [alpha + beta * xi for xi in x]
    ss_res = sum((y[i] - yhat[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - my) ** 2 for i in range(n))
    r2 = None if ss_tot <= 0 else 1.0 - ss_res / ss_tot
    return alpha, beta, r2

# -------------------------
# Data loaders
# -------------------------
def _load_monthly_trading_pnl() -> List[Dict[str, Any]]:
    data_dir = Path(get_data_dir())
    fp = data_dir / "monthly_profitability.json"
    if not fp.exists():
        # fallback path
        fp = data_dir / "profitability" / "monthly_profitability.json"
    if not fp.exists():
        return []

    obj = load_json_file(str(fp), default={})
    months = obj.get("months") if isinstance(obj, dict) else None
    if not isinstance(months, list):
        return []
    # we expect {label, trading_pnl_eur}
    return months

def _load_flows() -> Dict[str, Any]:
    data_dir = Path(get_data_dir())
    fp = data_dir / "portfolio" / "brick_flows.json"
    if not fp.exists():
        return {}
    return load_json_file(str(fp), default={}) or {}

def _find_btc_monthly_returns() -> Optional[Dict[str, float]]:
    """
    Lit data/market/ohlcv_combined.json au format:
      {"assets":[{"symbol":"BTCUSDT","candles":[...]}], ...}
    et calcule des returns mensuels BTC (dernier close du mois).
    Retour: dict {"YYYY-MM": return_float}
    """
    data_dir = Path(get_data_dir())
    fp = data_dir / "market" / "ohlcv_combined.json"
    if not fp.exists():
        return None

    obj = load_json_file(str(fp), default={})
    if not isinstance(obj, dict):
        return None

    assets = obj.get("assets")
    if not isinstance(assets, list) or not assets:
        return None

    # Trouve BTC (BTCUSDT idéalement)
    btc_asset = None
    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = str(a.get("symbol", "")).lower()
        if sym == "btcusdt" or ("btc" in sym):
            btc_asset = a
            break

    if not btc_asset:
        return None

    candles = btc_asset.get("candles")
    if not isinstance(candles, list) or len(candles) < 2:
        return None

    # Aide: convertit ts -> "YYYY-MM"
    def _ts_to_month(ts: Any) -> Optional[str]:
        if ts is None:
            return None
        # string datetime-ish
        if isinstance(ts, str):
            t = ts.strip()
            if len(t) >= 7:
                return t[:7]
            return None
        # numeric epoch (s or ms)
        if isinstance(ts, (int, float)):
            v = float(ts)
            # heuristique ms
            if v > 10_000_000_000:  # > ~year 2286 in seconds, so treat as ms
                v = v / 1000.0
            try:
                dt = datetime.fromtimestamp(v, tz=timezone.utc)
                return dt.strftime("%Y-%m")
            except Exception:
                return None
        return None

    last_close_by_month: Dict[str, float] = {}

    for it in candles:
        ts = None
        close = None

        # cas list: [ts, open, high, low, close, ...]
        if isinstance(it, list) and len(it) >= 5:
            ts = it[0]
            close = it[4]
        elif isinstance(it, dict):
            ts = it.get("ts") or it.get("time") or it.get("timestamp")
            close = it.get("close") or it.get("c")

        month = _ts_to_month(ts)
        c = _safe_float(close)
        if not month or c is None:
            continue

        # écrase => on garde le dernier rencontré du mois
        last_close_by_month[month] = c

    if len(last_close_by_month) < 2:
        return None

    months_sorted = sorted(last_close_by_month.keys())
    prev = None
    out: Dict[str, float] = {}

    for m in months_sorted:
        v = last_close_by_month[m]
        if prev is None or prev <= 0:
            out[m] = 0.0
        else:
            out[m] = (v - prev) / prev
        prev = v

    return out

# -------------------------
# Core computation (Crypto MVP)
# -------------------------
def _compute_crypto_metrics() -> Dict[str, Any]:
    months = _load_monthly_trading_pnl()
    flows_obj = _load_flows()

    bricks = (flows_obj.get("bricks") if isinstance(flows_obj, dict) else {}) or {}
    crypto_cfg = bricks.get("crypto") if isinstance(bricks, dict) else None
    crypto_flows = (crypto_cfg.get("flows") if isinstance(crypto_cfg, dict) else []) or []
    initial_capital = _safe_float((crypto_cfg or {}).get("initial_capital_eur"))
    if initial_capital is None:
        initial_capital = 0.0

    if initial_capital is None:
        initial_capital = 0.0


    # Build equity by month using trading pnl + flows
    # Start equity at initial_capital, and for each month:
    # V_end = V_prev + pnl + flow
    pnl_by_month: Dict[str, float] = {}
    for m in months:
        label = m.get("label")
        pnl = _safe_float(m.get("trading_pnl_eur"))
        if isinstance(label, str) and pnl is not None:
            pnl_by_month[_month_key(label)] = pnl

    all_months = sorted(pnl_by_month.keys())
    if not all_months:
        return {
            "id": "crypto",
            "name": "Crypto",
            "alpha": None,
            "beta": None,
            "r2": None,
            "corr": None,
            "return": None,
            "volatility": None,
            "n_points": 0,
            "note": "No monthly PnL data found"
        }

    equity: List[Tuple[str, float]] = []
    v = float(initial_capital)
    for month in all_months:
        pnl = pnl_by_month.get(month, 0.0)
        flow = _sum_flows_for_month(crypto_flows, month)
        v = v + pnl + flow
        equity.append((month, v))

    # returns
    rets = _compute_returns_from_equity(equity)
    ret_values = [r for _, r in rets][1:]  # ignore first (0)
    vol = _std(ret_values) if ret_values else None
    total_return = None
    if len(equity) >= 2 and equity[0][1] > 0:
        total_return = (equity[-1][1] - equity[0][1]) / equity[0][1]

    # benchmark BTC returns (optional)
    btc_rets = _find_btc_monthly_returns()
    bench_vals: List[float] = []
    port_vals: List[float] = []

    if btc_rets:
        for month, r in rets:
            if month in btc_rets:
                bench_vals.append(float(btc_rets[month]))
                port_vals.append(float(r))

    alpha = beta = r2 = corr = None
    if len(bench_vals) >= 2 and len(port_vals) >= 2:
        alpha, beta, r2 = _linreg_alpha_beta(port_vals, bench_vals)
        corr = _corr(port_vals, bench_vals)

    return {
        "id": "crypto",
        "name": "Crypto",
        "alpha": alpha,
        "beta": beta,
        "r2": r2,
        "corr": corr,
        "return": total_return,
        "volatility": vol,
        "n_points": max(0, len(ret_values)),
        "equity_months": equity[-6:],  # debug light
    }

@router.get("/overview")
def alpha_beta_overview() -> Dict[str, Any]:
    # MVP: seulement Crypto pour l'instant, multi-briques ensuite
    crypto = _compute_crypto_metrics()

    payload: Dict[str, Any] = {
        "as_of": _utc_now(),
        "benchmark": {"id": "BTC", "name": "BTC (monthly, best-effort)"},
        "bricks": [crypto],
    }

    # si aucune donnée exploitable => empty state (compatible UI)
    if (crypto.get("n_points") or 0) == 0:
        return {
            "detail": "No alpha/beta data",
            "generated_at": _utc_now(),
            "bricks": [],
            "benchmarks": [],
        }

    return payload
