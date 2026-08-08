from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter

router = APIRouter(tags=["crypto-overview"])

TRADE_SIM_PATH = Path("/opt/nsc/data/preprod/trading/trade_simulation.json")
SELECTED_TOKENS_PATH = Path("/opt/nsc/app/src/v2/data/selected_tokens.json")
SENTIMENT_OVERVIEW_PATH = Path("/opt/nsc/data/preprod/sentiment_overview.json")
SENTIMENT_STATE_PATH = Path("/opt/nsc/data/preprod/state/sentiment_state.json")
AVERAGE_SENTIMENT_PATH = Path("/opt/nsc/data/preprod/reports/average_sentiment.json")

# ICO / whales conservés mais relégués plus bas
ICO_CANDIDATES_PATH = Path("/opt/nsc/app/data/ico/ico_candidates.json")
ICO_SCREENED_PATH = Path("/opt/nsc/app/data/ico/ico_screened.json")
ICO_SCORED_PATH = Path("/opt/nsc/app/data/ico/ico_scored.json")
ICO_ALLOCATION_PATH = Path("/opt/nsc/app/data/ico/ico_allocation.json")
WHALES_LEADERBOARD_PATH = Path("/opt/nsc/app/data/intelligence/whales_leaderboard.json")
SPOT_PRICES_PATH = Path("/opt/nsc/data/preprod/market/crypto_spot_prices.json")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_spot_prices() -> Dict[str, float]:
    data = load_json(SPOT_PRICES_PATH, default={}) or {}
    out: Dict[str, float] = {}

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (int, float)):
                out[str(k).upper()] = float(v)

        for k, v in data.items():
            if not isinstance(v, dict):
                continue
            price = None
            for field in ("price_eur", "eur", "current_price_eur", "price", "usd", "current_price"):
                if v.get(field) is not None:
                    try:
                        price = float(v.get(field))
                        break
                    except Exception:
                        pass
            if price is not None:
                out[str(k).upper()] = price

        items = data.get("items")
        if isinstance(items, list):
            for row in items:
                if not isinstance(row, dict):
                    continue
                token = str(row.get("token") or row.get("symbol") or "").upper().strip()
                if not token:
                    continue
                price = None
                for field in ("price_eur", "eur", "current_price_eur", "price", "usd", "current_price"):
                    if row.get(field) is not None:
                        try:
                            price = float(row.get(field))
                            break
                        except Exception:
                            pass
                if price is not None:
                    out[token] = price

    elif isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            token = str(row.get("token") or row.get("symbol") or "").upper().strip()
            if not token:
                continue
            price = None
            for field in ("price_eur", "eur", "current_price_eur", "price", "usd", "current_price"):
                if row.get(field) is not None:
                    try:
                        price = float(row.get(field))
                        break
                    except Exception:
                        pass
            if price is not None:
                out[token] = price

    return out


@router.get("/api/crypto/overview")
def crypto_overview() -> Dict[str, Any]:
    trade_sim = load_json(TRADE_SIM_PATH, default=[]) or []
    selected_tokens = load_json(SELECTED_TOKENS_PATH, default=[]) or []
    sentiment_overview = load_json(SENTIMENT_OVERVIEW_PATH, default={}) or {}
    sentiment_state = load_json(SENTIMENT_STATE_PATH, default={}) or {}
    average_sentiment = load_json(AVERAGE_SENTIMENT_PATH, default={}) or {}

    ico_candidates = load_json(ICO_CANDIDATES_PATH, default=[]) or []
    ico_screened = load_json(ICO_SCREENED_PATH, default=[]) or []
    ico_scored = load_json(ICO_SCORED_PATH, default=[]) or []
    ico_allocation = load_json(ICO_ALLOCATION_PATH, default=[]) or []
    whales = load_json(WHALES_LEADERBOARD_PATH, default=[]) or []

    trades = _as_list(trade_sim)
    tokens = _as_list(selected_tokens)
    top_tokens = _as_list(sentiment_overview.get("top_tokens", []))
    whales_rows = _as_list(whales)

    spot_prices = load_spot_prices()

    exposure_eur = 0.0
    pnl_total_eur = 0.0
    enriched_trades = []

    for item in trades:
        if not isinstance(item, dict):
            continue

        token = str(item.get("token", "")).upper()
        notional = _safe_float(item.get("notional_eur", item.get("amount", 0.0)), 0.0)
        exposure_eur += notional

        entry_price = _safe_float(item.get("entry_price_eur"), 0.0)
        quantity_units = _safe_float(item.get("quantity_units"), 0.0)
        current_price = _safe_float(item.get("current_price_eur"), 0.0)

        if current_price <= 0:
            current_price = _safe_float(spot_prices.get(token), 0.0)

        entry_value = _safe_float(item.get("entry_value_eur"), notional)
        current_value = _safe_float(item.get("current_value_eur"), notional)
        pnl_eur = _safe_float(item.get("pnl_eur"), 0.0)

        if entry_price > 0 and quantity_units > 0 and current_price > 0:
            entry_value = quantity_units * entry_price
            current_value = quantity_units * current_price
            pnl_eur = round(current_value - entry_value, 2)

        pnl_total_eur += pnl_eur

        enriched = dict(item)
        enriched["current_price_eur"] = round(current_price, 8) if current_price > 0 else None
        enriched["entry_value_eur"] = round(entry_value, 2)
        enriched["current_value_eur"] = round(current_value, 2)
        enriched["pnl_eur"] = pnl_eur
        enriched_trades.append(enriched)

    trades = enriched_trades

    avg_score = None
    if isinstance(sentiment_state, dict) and sentiment_state.get("avg_score") is not None:
        avg_score = _safe_float(sentiment_state.get("avg_score"), 0.0)
    elif isinstance(sentiment_overview, dict) and isinstance(sentiment_overview.get("sentiment"), dict):
        avg_score = _safe_float(sentiment_overview["sentiment"].get("avg_score"), 0.0)

    bucket = None
    if isinstance(sentiment_state, dict):
        bucket = sentiment_state.get("bucket")
    if not bucket and isinstance(sentiment_overview, dict):
        bucket = (sentiment_overview.get("sentiment") or {}).get("bucket")

    avg_whale_win_rate = None
    best_30d_pnl = None
    if whales_rows:
        rates = []
        pnls = []
        for row in whales_rows:
            if not isinstance(row, dict):
                continue
            if row.get("win_rate_30d") is not None:
                rates.append(_safe_float(row.get("win_rate_30d"), 0.0))
            if row.get("pnl_30d") is not None:
                pnls.append(_safe_float(row.get("pnl_30d"), 0.0))
        if rates:
            avg_whale_win_rate = sum(rates) / len(rates)
        if pnls:
            best_30d_pnl = max(pnls)

    return {
        "header": {
            "name": "Crypto",
            "status": "PREPROD",
            "env": "PREPROD",
            "mode": "SIMULATED_ONLY",
            "regime": "neutral",
        },
        "kpis": {
            "selected_tokens": len(trades) if trades else len(tokens),
            "orders": len(trades),
            "open_positions": len(trades),
            "pnl_eur": round(pnl_total_eur, 2),
            "exposure_eur": round(sum(_safe_float(x.get("current_value_eur", x.get("notional_eur", x.get("amount", 0.0))), 0.0) for x in trades), 2),
            "sentiment_score": avg_score,
            "sentiment_bucket": bucket or "unknown",
        },
        "signals": {
            "selected_tokens": tokens,
            "sentiment_state": sentiment_state if isinstance(sentiment_state, dict) else {},
            "average_sentiment": average_sentiment if isinstance(average_sentiment, dict) else {},
            "top_tokens": top_tokens[:10],
            "counts": sentiment_overview.get("counts", {}) if isinstance(sentiment_overview, dict) else {},
        },
        "execution": {
            "trades": trades,
        },
        "explainability": {
            "summary": [
                "Crypto page now prioritizes real runtime data: selected tokens, sentiment, simulated trades, and exposure.",
                "PnL remains unavailable until trade entries include a usable entry price or a mark-to-market layer is added.",
                "ICO pipeline and whales are preserved as secondary exploration blocks."
            ]
        },
        "ico": {
            "candidates_count": len(_as_list(ico_candidates)),
            "screened_count": len(_as_list(ico_screened)),
            "scored_count": len(_as_list(ico_scored)),
            "allocation_count": len(_as_list(ico_allocation)),
            "candidates": _as_list(ico_candidates)[:10],
            "screened": _as_list(ico_screened)[:10],
            "scored": _as_list(ico_scored)[:10],
            "allocation": _as_list(ico_allocation)[:10],
        },
        "whales": {
            "tracked_wallets": len(whales_rows),
            "average_win_rate": avg_whale_win_rate,
            "best_30d_pnl": best_30d_pnl,
            "rows": whales_rows[:10],
        },
    }
